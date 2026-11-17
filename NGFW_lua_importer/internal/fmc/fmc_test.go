package fmc

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

type fakeDetector struct {
	uuid, name string
	active     bool
	editable   bool
	lua        string
}

// fakeFMC mimics the FMC Web UI endpoints used by the client.
type fakeFMC struct {
	mu          sync.Mutex
	apps        map[string]int
	detectors   []*fakeDetector
	uploads     map[string]string
	rejectLua   bool
	dropLua     bool
	deleted     []string
	activateOK  bool
	loggedOut   bool
	alwaysEmpty bool
	calls       []string
}

func newFake() *fakeFMC {
	return &fakeFMC{
		apps:      map[string]int{"facebook": 1},
		detectors: []*fakeDetector{{uuid: "builtin-1", name: "Facebook", active: true}},
		uploads:   map[string]string{}, activateOK: true,
	}
}

func (f *fakeFMC) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	f.mu.Lock()
	defer f.mu.Unlock()
	switch r.URL.Path {
	case "/ui/login":
		w.Write([]byte("login"))
	case "/login.cgi":
		r.ParseForm()
		if r.Form.Get("password") != "pw" {
			w.WriteHeader(200)
			return
		}
		f.loggedOut = false
		http.SetCookie(w, &http.Cookie{Name: "CGISESSID", Value: "s1", Path: "/"})
		w.Header().Set("Location", "/ddd/")
		w.WriteHeader(302)
	case "/ddd/":
		if c, err := r.Cookie("CGISESSID"); err != nil || c.Value != "s1" {
			w.WriteHeader(302)
			return
		}
		w.Write([]byte(`<title>Cisco Secure Firewall Management Center for VMware 10.0.1 Build 1 (FMC01) - admin</title><script>var sf_action_id = "abc123"; x={"fmcBuild":"10.0.1-1"}</script>`))
	case "/RNADetector/detectors.cgi":
		r.ParseMultipartForm(1 << 20)
		file, _, _ := r.FormFile("lua_upload")
		data, _ := io.ReadAll(file)
		if f.rejectLua {
			w.Write([]byte(`<html>FILENAME=x.lua!!ERROR=<b>Syntax error</b>!!</html>`))
			return
		}
		f.uploads[r.FormValue("detector_uuid")] = string(data)
		w.Write([]byte(`<html>FILENAME=x.lua!!SUCCESS=1!!</html>`))
	case "/pjb.cgi":
		r.ParseForm()
		if f.loggedOut || f.alwaysEmpty {
			w.Write([]byte(`{"error":null}`))
			return
		}
		if r.Form.Get("sf_action_id") != "abc123" {
			w.Write([]byte(`{"error":{"text":"bad token"}}`))
			return
		}
		fn := r.Form.Get("function")
		f.calls = append(f.calls, shortName(fn))
		var params []json.RawMessage
		json.Unmarshal([]byte(r.Form.Get("parameters")), &params)
		f.pjb(w, shortName(fn), params)
	default:
		w.WriteHeader(404)
	}
}

func (f *fakeFMC) pjb(w http.ResponseWriter, fn string, params []json.RawMessage) {
	reply := func(v any) { json.NewEncoder(w).Encode(map[string]any{"data": v}) }
	switch fn {
	case "getFilterList":
		var apps []map[string]any
		for n := range f.apps {
			apps = append(apps, map[string]any{"appName": n})
		}
		reply(map[string]any{
			"apps": map[string]any{"Applications": apps},
			"filters": []any{map[string]any{"key": "risk", "list": []any{map[string]any{"id": 1, "name": 1}}}, map[string]any{"key": "category", "list": []any{
				map[string]any{"id": "7", "name": "others"}, map[string]any{"id": 12, "name": "multimedia (TV/video)"},
			}}},
		})
	case "saveApp":
		var a map[string]any
		json.Unmarshal(params[0], &a)
		id := 1000000 + len(f.apps)
		f.apps[strings.ToLower(a["appName"].(string))] = id
		reply(map[string]any{"appId": fmt.Sprint(id)})
	case "setDetector":
		var mode string
		json.Unmarshal(params[0], &mode)
		var d map[string]any
		json.Unmarshal(params[2], &d)
		if mode == "new" {
			fd := &fakeDetector{uuid: fmt.Sprintf("uuid-%d", len(f.detectors)), name: d["name"].(string), editable: true}
			f.detectors = append(f.detectors, fd)
			reply(map[string]any{"detector": map[string]any{"uuid": fd.uuid}})
			return
		}
		var uuid string
		json.Unmarshal(params[1], &uuid)
		lua := f.uploads[uuid]
		if f.dropLua {
			lua = ""
		}
		for _, fd := range f.detectors {
			if fd.uuid == uuid {
				fd.lua = lua
			}
		}
		reply(map[string]any{"detector": map[string]any{"data": map[string]any{"lua": strings.ReplaceAll(lua, "\n", "\r\n")}}})
	case "initDetectorEditorForAllApps":
		reply(map[string]any{})
	case "deleteDetectors":
		var uuids []string
		json.Unmarshal(params[0], &uuids)
		f.deleted = append(f.deleted, uuids...)
		reply(1)
	case "activateDetectors":
		var uuids []string
		json.Unmarshal(params[0], &uuids)
		if f.activateOK {
			for _, fd := range f.detectors {
				for _, u := range uuids {
					if fd.uuid == u {
						fd.active = true
					}
				}
			}
		}
		reply(1)
	case "getDetectorList":
		var off, limit int
		json.Unmarshal(params[2], &off)
		json.Unmarshal(params[3], &limit)
		var rows []any
		for i, fd := range f.detectors {
			if i < off || i >= off+limit {
				continue
			}
			rows = append(rows, map[string]any{"uuid": fd.uuid, "data": map[string]any{
				"name": fd.name, "active": b2i(fd.active), "editable": fmt.Sprint(b2i(fd.editable)),
			}})
		}
		reply(map[string]any{"totalRows": len(f.detectors), "detectors": rows})
	default:
		json.NewEncoder(w).Encode(map[string]any{"error": map[string]any{"text": "unknown " + fn}})
	}
}

func b2i(b bool) int {
	if b {
		return 1
	}
	return 0
}

func setup(t *testing.T) (*fakeFMC, *Client) {
	t.Helper()
	f := newFake()
	srv := httptest.NewTLSServer(f)
	t.Cleanup(srv.Close)
	c, err := New(srv.URL, "admin", "pw", false)
	if err != nil {
		t.Fatal(err)
	}
	c.PollEvery = 10 * time.Millisecond
	if err := c.Login(); err != nil {
		t.Fatal(err)
	}
	return f, c
}

const sampleLua = "-- detector\nrequire \"DetectorCommon\"\nlocal x = 1\n"

func TestNormalizeHost(t *testing.T) {
	cases := map[string]string{"10.0.0.1": "10.0.0.1", " https://fmc.local:8443/ ": "fmc.local:8443", "fmc/": "fmc"}
	for in, want := range cases {
		if got, err := NormalizeHost(in); err != nil || got != want {
			t.Errorf("NormalizeHost(%q) = %q, %v", in, got, err)
		}
	}
	for _, bad := range []string{"", "a b", "x;rm"} {
		if _, err := NormalizeHost(bad); err == nil {
			t.Errorf("NormalizeHost(%q) accepted", bad)
		}
	}
}

func TestLoginWrongPassword(t *testing.T) {
	srv := httptest.NewTLSServer(newFake())
	defer srv.Close()
	c, _ := New(srv.URL, "admin", "nope", false)
	if err := c.Login(); err == nil || !strings.Contains(err.Error(), "login failed") {
		t.Fatalf("expected login failure, got %v", err)
	}
}

func TestVerifyTLSRejectsSelfSigned(t *testing.T) {
	srv := httptest.NewTLSServer(newFake())
	defer srv.Close()
	c, _ := New(srv.URL, "admin", "pw", true)
	if err := c.Login(); err == nil {
		t.Fatal("expected a certificate error")
	}
}

func TestImportActivateFlow(t *testing.T) {
	f, c := setup(t)
	if v := c.ServerVersion(); v != "10.0.1 (build 1)" {
		t.Fatalf("ServerVersion = %q", v)
	}
	res, err := c.Import(Spec{AppName: "Demo_App", Lua: []byte(sampleLua), Category: "Multimedia (TV/Video)", Risk: 2, BusinessRelevance: 3, Description: "d"})
	if err != nil {
		t.Fatal(err)
	}
	if res.Status != "imported" || res.UUID == "" || res.Category != "multimedia (TV/video)" || !res.CategoryExact {
		t.Fatalf("unexpected result %+v", res)
	}
	if f.uploads[res.UUID] != sampleLua {
		t.Fatal("Lua was not uploaded unchanged")
	}

	res2, err := c.Import(Spec{AppName: "demo_app", Lua: []byte(sampleLua)})
	if err != nil || res2.Status != "skipped" {
		t.Fatalf("duplicate import should be skipped: %+v %v", res2, err)
	}

	names := map[string]bool{"demo_app": true}
	state, err := c.Activate([]string{res.UUID}, names, func(string) {})
	if err != nil || !state[res.UUID] {
		t.Fatalf("activation failed: %v %v", state, err)
	}
	list, _ := c.Detectors(map[string]bool{"facebook": true})
	if len(list["facebook"]) != 1 || list["facebook"][0].Editable {
		t.Fatalf("built-in detector parsed wrongly: %+v", list)
	}
}

func TestUnknownCategoryFallsBack(t *testing.T) {
	_, c := setup(t)
	res, err := c.Import(Spec{AppName: "Other_App", Lua: []byte(sampleLua), Category: "no such"})
	if err != nil || res.Category != "others" || res.CategoryExact || !strings.Contains(res.Message, "not found") {
		t.Fatalf("unexpected %+v %v", res, err)
	}
}

func TestRejectedUploadRollsBack(t *testing.T) {
	f, c := setup(t)
	f.rejectLua = true
	_, err := c.Import(Spec{AppName: "Bad_App", Lua: []byte(sampleLua)})
	if err == nil || !strings.Contains(err.Error(), "Syntax error") {
		t.Fatalf("expected rejection, got %v", err)
	}
	if len(f.deleted) != 1 {
		t.Fatalf("half-created detector was not deleted: %v", f.deleted)
	}
}

func TestLuaMissingAfterSaveRollsBack(t *testing.T) {
	f, c := setup(t)
	f.dropLua = true
	if _, err := c.Import(Spec{AppName: "Lost_App", Lua: []byte(sampleLua)}); err == nil {
		t.Fatal("expected verification failure")
	}
	if len(f.deleted) != 1 {
		t.Fatal("detector was not rolled back")
	}
}

func TestActivationTimeout(t *testing.T) {
	f, c := setup(t)
	res, _ := c.Import(Spec{AppName: "Slow_App", Lua: []byte(sampleLua)})
	f.activateOK = false
	c.PollEvery = time.Millisecond
	// FMC finishes activation only after the call returned; polling must pick it up.
	done := make(chan struct{})
	go func() {
		defer close(done)
		time.Sleep(50 * time.Millisecond)
		f.mu.Lock()
		f.activateOK = true
		for _, d := range f.detectors {
			if d.uuid == res.UUID {
				d.active = true
			}
		}
		f.mu.Unlock()
	}()
	state, err := c.Activate([]string{res.UUID}, map[string]bool{"slow_app": true}, func(string) {})
	<-done
	if err != nil || !state[res.UUID] {
		t.Fatalf("polling did not observe activation: %v %v", state, err)
	}
}

func TestComparable(t *testing.T) {
	if Comparable([]byte("a\r\nb\x00\xe4 ")) != "a\nb" {
		t.Fatal("Comparable mismatch")
	}
}

func TestParseVersion(t *testing.T) {
	cases := map[string]string{
		`x "fmcBuild":"7.4.2-172" y`: "7.4.2 (build 172)",
		`<title>Cisco Secure Firewall Management Center for VMware 7.2.5.1 Build 29 (FMC) - admin</title>`: "7.2.5.1 (build 29)",
		`nothing`: "",
	}
	for in, want := range cases {
		if got := parseVersion([]byte(in)); got != want {
			t.Errorf("parseVersion(%q) = %q, want %q", in, got, want)
		}
	}
}

func TestDroppedSessionIsRecovered(t *testing.T) {
	f, c := setup(t)
	f.loggedOut = true
	list, err := c.Detectors(map[string]bool{"facebook": true})
	if err != nil || len(list["facebook"]) != 1 {
		t.Fatalf("relogin did not recover: %v %v", list, err)
	}
}

func TestLoggedOutSessionIsReported(t *testing.T) {
	f, c := setup(t)
	f.alwaysEmpty = true
	_, err := c.Import(Spec{AppName: "X_App", Lua: []byte(sampleLua)})
	if err == nil || !strings.Contains(err.Error(), "logged out") {
		t.Fatalf("expected a clear logged-out error, got %v", err)
	}
}
