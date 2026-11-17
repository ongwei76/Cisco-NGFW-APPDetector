"""Import custom Lua detectors into FMC (Policies > Application Detectors).

FMC has no public REST API for custom application detectors, so this replays
the calls the FMC Web UI makes (verified on FMC 10.0):

1. ``SF::Cache::RNADetector::saveApp`` creates the application with its
   category, risk and business relevance.
2. ``setDetector("new", …)`` creates an empty *Advanced* (``protocol=custom``)
   detector for it.
3. ``/RNADetector/detectors.cgi`` uploads the Lua for that detector.
4. ``setDetector("save", …)`` stores the detector with the uploaded Lua.

Imported detectors stay Inactive; activating and deploying is left to the
FMC administrator. Deleting the detector also removes the custom application,
which is used to roll back a partially imported detector.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import requests

log = logging.getLogger(__name__)

ACTION_ID_RE = re.compile(r'sf_action_id\s*=\s*"([0-9a-fA-F]+)"')
UPLOAD_RESULT_RE = re.compile(r"FILENAME=[^!]*!!(SUCCESS|ERROR)=([^!<]*)")


def _comparable(lua: bytes) -> str:
    """Lua code with line endings and non-ASCII bytes (GBK/UTF-8 comments) dropped."""
    return re.sub(rb"[^\x20-\x7e\n\t]", b"", lua.replace(b"\r\n", b"\n")).decode("ascii").strip()


class FmcImportError(Exception):
    """FMC rejected an import step."""


@dataclass
class DetectorSpec:
    app_name: str
    lua: bytes
    description: str
    category: str
    risk: int
    business_relevance: int


@dataclass
class FmcDetectorImporter:
    """Speaks the FMC Web UI JSON endpoint ``/pjb.cgi`` with a CGISESSID session."""

    base: str
    session: requests.Session
    relogin: Callable[[], None]
    timeout: float = 30.0
    _action_id: str = field(default="", init=False)
    _apps: Optional[set[str]] = field(default=None, init=False)
    _categories: Optional[dict[str, tuple[int, str]]] = field(default=None, init=False)

    def connect(self) -> None:
        """Fetch the per-session CSRF token (``sf_action_id``), re-logging in once if needed."""
        for attempt in (0, 1):
            response = self.session.get(
                f"{self.base}/ddd/", allow_redirects=False, timeout=self.timeout,
            )
            match = ACTION_ID_RE.search(response.text) if response.status_code == 200 else None
            if match:
                self._action_id = match.group(1)
                return
            if attempt == 0:
                self.relogin()
        raise FmcImportError("FMC Web UI session could not be established")

    def _call(self, function: str, params: list[Any], page: str = "DetectorList") -> Any:
        if not self._action_id:
            self.connect()
        response = self.session.post(
            f"{self.base}/pjb.cgi",
            data={
                "function": function,
                "parameters": json.dumps(params),
                "get_all_errors": "1",
                "sf_action_id": self._action_id,
                "ss": page,
            },
            headers={"Referer": f"{self.base}/ddd/"},
            timeout=self.timeout,
        )
        try:
            payload = response.json()
        except ValueError as e:
            raise FmcImportError(f"{function.rsplit('::', 1)[-1]}: unexpected FMC response (HTTP {response.status_code})") from e
        if isinstance(payload, dict) and payload.get("error"):
            error = payload["error"]
            text = error.get("text") if isinstance(error, dict) else str(error)
            raise FmcImportError(f"{function.rsplit('::', 1)[-1]}: {text or 'FMC error'}")
        return payload.get("data") if isinstance(payload, dict) else None

    def _load_catalog(self) -> None:
        data = self._call("SF::Cache::RNADetector::getFilterList", []) or {}
        apps = (data.get("apps") or {}).get("Applications") or []
        self._apps = {str(a.get("appName", "")).casefold() for a in apps if a.get("appName")}
        categories: dict[str, tuple[int, str]] = {}
        for flt in data.get("filters") or []:
            if flt.get("key") == "category":
                for item in flt.get("list") or []:
                    try:
                        categories[str(item["name"]).casefold()] = (int(item["id"]), str(item["name"]))
                    except (KeyError, TypeError, ValueError):
                        continue
        if not categories:
            raise FmcImportError("FMC did not return its application categories")
        self._categories = categories

    def app_exists(self, app_name: str) -> bool:
        if self._apps is None:
            self._load_catalog()
        return app_name.casefold() in self._apps

    def resolve_category(self, name: str) -> tuple[int, str, bool]:
        """Return ``(tag id, FMC name, exact)``; unknown names fall back to "others"."""
        if self._categories is None:
            self._load_catalog()
        found = self._categories.get((name or "").casefold())
        if found:
            return found[0], found[1], True
        fallback = self._categories.get("others") or next(iter(self._categories.values()))
        return fallback[0], fallback[1], False

    def import_detector(self, spec: DetectorSpec) -> dict[str, Any]:
        if self.app_exists(spec.app_name):
            return {"status": "skipped", "message": "application already exists in FMC"}
        tag_id, category, exact = self.resolve_category(spec.category)
        app = self._call("SF::Cache::RNADetector::saveApp", [{
            "appName": spec.app_name,
            "appId": -1,
            "risk_index": spec.risk,
            "productivity_index": spec.business_relevance,
            "appDescription": spec.description,
            "categories": [{"tagId": tag_id, "tagType": "category", "tagName": category}],
            "tags": [],
            "isDecryptedOnlyDetector": 0,
        }]) or {}
        try:
            app_id = int(app["appId"])
        except (KeyError, TypeError, ValueError) as e:
            raise FmcImportError("saveApp: FMC did not return an application id") from e
        self._apps.add(spec.app_name.casefold())

        orphan = f"remove the empty application {spec.app_name} in FMC before retrying"
        try:
            created = self._call("SF::Cache::RNADetector::setDetector", ["new", None, {
                "name": spec.app_name, "domainName": "", "viewable": 1, "editable": 1, "active": 0,
                "clientServer": "", "patterns": [], "appId": app_id, "pcaps": {},
                "description": spec.description, "protocol": "custom", "lua": 0,
            }]) or {}
        except FmcImportError as e:
            raise FmcImportError(f"{e}; {orphan}") from e
        uuid = str((created.get("detector") or {}).get("uuid") or "")
        if not uuid:
            raise FmcImportError(f"setDetector: no detector was created; {orphan}")
        try:
            self._upload_and_save(spec, uuid, app_id)
        except Exception:
            self._rollback(uuid)
            raise
        return {
            "status": "imported",
            "uuid": uuid,
            "app_id": app_id,
            "category": category,
            "category_exact": exact,
            "message": "imported (Inactive)" if exact else f"imported (Inactive); category not found on this FMC, used '{category}'",
        }

    def _upload_and_save(self, spec: DetectorSpec, uuid: str, app_id: int) -> None:
        self._call("SF::Cache::RNADetector::initDetectorEditorForAllApps", [uuid], page="DetectorEditor")
        response = self.session.post(
            f"{self.base}/RNADetector/detectors.cgi",
            data={"sf_action_id": self._action_id, "detector_uuid": uuid},
            files={"lua_upload": (f"{spec.app_name}.lua", spec.lua, "application/octet-stream")},
            headers={"Referer": f"{self.base}/ddd/"},
            timeout=self.timeout,
        )
        match = UPLOAD_RESULT_RE.search(response.text)
        if not match or match.group(1) != "SUCCESS":
            reason = re.sub(r"<[^>]+>", " ", match.group(2)).strip(" -") if match else f"HTTP {response.status_code}"
            raise FmcImportError(f"Lua upload rejected by FMC: {reason}")
        saved = self._call("SF::Cache::RNADetector::setDetector", ["save", uuid, {
            "service_name": spec.app_name, "viewable": 1, "clientServer": "", "protocol": "custom",
            "service_id": app_id, "patterns": [], "active": 0, "appId": app_id, "lua": 1,
            "description": spec.description, "subtype": 5, "ports": "", "pcaps": {},
            "editable": 1, "name": spec.app_name, "domainName": "",
        }], page="DetectorEditor") or {}
        stored = ((saved.get("detector") or {}).get("data") or {}).get("lua")
        if not isinstance(stored, str) or _comparable(spec.lua) not in _comparable(stored.encode("utf-8")):
            raise FmcImportError("FMC saved the detector without the uploaded Lua")

    def _rollback(self, uuid: str) -> None:
        try:
            self._call("SF::Cache::RNADetector::deleteDetectors", [[uuid]])
            self._apps = None
        except Exception:
            log.exception("Rolling back FMC detector %s failed", uuid)
