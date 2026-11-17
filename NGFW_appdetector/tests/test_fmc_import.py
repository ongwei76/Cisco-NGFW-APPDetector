import json
from typing import Any

import pytest

from ngfw_appdetector.ngfw_collector.fmc_import import DetectorSpec, FmcDetectorImporter, FmcImportError

BASE = "https://fmc"
LUA = b'require "DetectorCommon"\r\nDetectorPackageInfo = { name = "Zz" }\r\n'


class _Resp:
    def __init__(self, status: int = 200, text: str = "", payload: Any = None) -> None:
        self.status_code = status
        self.text = text if payload is None else json.dumps(payload)
        self._payload = payload

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class _FakeFmc:
    def __init__(self) -> None:
        self.logged_in = False
        self.calls: list[tuple[str, Any]] = []
        self.upload_ok = True
        self.stored_lua: str = ""
        self.save_echo = True

    def get(self, url: str, allow_redirects: bool = True, timeout: float = 0) -> _Resp:
        assert url == f"{BASE}/ddd/"
        if not self.logged_in:
            return _Resp(302)
        return _Resp(200, 'var x; sf_action_id = "abc123";')

    def post(self, url: str, data: dict, files: Any = None, headers: Any = None, timeout: float = 0) -> _Resp:
        assert data["sf_action_id"] == "abc123"
        if url.endswith("/RNADetector/detectors.cgi"):
            self.calls.append(("upload", data["detector_uuid"]))
            self.stored_lua = files["lua_upload"][1].decode()
            return _Resp(200, "FILENAME=Zz.lua!!SUCCESS=1" if self.upload_ok else "FILENAME=Zz.lua!!ERROR=-bad lua!!")
        function = data["function"].rsplit("::", 1)[-1]
        params = json.loads(data["parameters"])
        self.calls.append((function, params))
        if function == "getFilterList":
            return _Resp(payload={"data": {
                "apps": {"Applications": [{"appName": "Existing"}]},
                "filters": [{"key": "category", "list": [{"id": 119, "name": "financial"}, {"id": 7, "name": "others"}]}],
            }})
        if function == "saveApp":
            return _Resp(payload={"data": {"appId": "1000017"}})
        if function == "setDetector" and params[0] == "new":
            return _Resp(payload={"data": {"detector": {"uuid": "u-1"}}})
        if function == "setDetector" and params[0] == "save":
            lua = "----CSC header\n" + self.stored_lua.replace("\r\n", "\n") if self.save_echo else ""
            return _Resp(payload={"data": {"detector": {"data": {"lua": lua}}}})
        if function in ("initDetectorEditorForAllApps", "deleteDetectors"):
            return _Resp(payload={"data": {}})
        raise AssertionError(function)


def _importer(fake: _FakeFmc) -> FmcDetectorImporter:
    def relogin() -> None:
        fake.logged_in = True
    return FmcDetectorImporter(base=BASE, session=fake, relogin=relogin)


def _spec(name: str = "Zz", category: str = "Financial") -> DetectorSpec:
    return DetectorSpec(app_name=name, lua=LUA, description="d", category=category, risk=2, business_relevance=4)


def test_import_creates_app_and_detector_with_category() -> None:
    fake = _FakeFmc()
    importer = _importer(fake)
    importer.connect()
    result = importer.import_detector(_spec())
    assert result["status"] == "imported" and result["category"] == "financial" and result["category_exact"]
    save_app = next(p for f, p in fake.calls if f == "saveApp")[0]
    assert save_app["categories"] == [{"tagId": 119, "tagType": "category", "tagName": "financial"}]
    assert (save_app["risk_index"], save_app["productivity_index"]) == (2, 4)
    save = next(p for f, p in fake.calls if f == "setDetector" and p[0] == "save")
    assert save[1] == "u-1" and save[2]["active"] == 0 and save[2]["appId"] == 1000017
    assert ("upload", "u-1") in fake.calls
    assert importer.import_detector(_spec())["status"] == "skipped"
    assert importer.import_detector(_spec("existing"))["status"] == "skipped"


def test_unknown_category_falls_back_to_others() -> None:
    fake = _FakeFmc()
    fake.logged_in = True
    result = _importer(fake).import_detector(_spec(category="not-on-this-fmc"))
    assert result["category"] == "others" and not result["category_exact"]
    assert "others" in result["message"]


@pytest.mark.parametrize("failure", ["upload", "save"])
def test_failed_upload_rolls_back_the_detector(failure: str) -> None:
    fake = _FakeFmc()
    fake.logged_in = True
    if failure == "upload":
        fake.upload_ok = False
    else:
        fake.save_echo = False
    importer = _importer(fake)
    with pytest.raises(FmcImportError):
        importer.import_detector(_spec())
    assert ("deleteDetectors", [["u-1"]]) in fake.calls
    fake.upload_ok = fake.save_echo = True
    assert importer.import_detector(_spec())["status"] == "imported"


def test_connect_fails_when_login_does_not_help() -> None:
    fake = _FakeFmc()
    importer = FmcDetectorImporter(base=BASE, session=fake, relogin=lambda: None)
    with pytest.raises(FmcImportError):
        importer.connect()


def test_gbk_lua_is_verified_without_its_non_ascii_comments() -> None:
    fake = _FakeFmc()
    fake.logged_in = True
    gbk = "-- 招商证券 — detector\r\n".encode("gbk") + LUA
    spec = DetectorSpec(app_name="Gbk", lua=gbk, description="d", category="financial", risk=2, business_relevance=3)
    original_post = fake.post

    def post(url, data, files=None, headers=None, timeout=0):
        if files:
            files = {"lua_upload": (files["lua_upload"][0], files["lua_upload"][1].decode("latin-1").encode(), "")}
        return original_post(url, data, files=files, headers=headers, timeout=timeout)
    fake.post = post
    assert _importer(fake).import_detector(spec)["status"] == "imported"
