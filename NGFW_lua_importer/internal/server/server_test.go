package server

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"ngfw-lua-importer/internal/fmc"
	"ngfw-lua-importer/internal/library"
)

type fakeGitHub map[string]string

func (f fakeGitHub) RoundTrip(r *http.Request) (*http.Response, error) {
	body, ok := f[r.URL.Host+r.URL.Path]
	status := 200
	if !ok {
		status = 404
	}
	return &http.Response{StatusCode: status, Body: io.NopCloser(strings.NewReader(body)), Header: http.Header{}, Request: r}, nil
}

const luaA = "-- A\n"

func testLibrary() *library.Client {
	commit := strings.Repeat("e", 40)
	sum := sha256.Sum256([]byte(luaA))
	idx := fmt.Sprintf(`{"entries":[
	 {"lua_path":"library/New_App/1/New_App.lua","sha256":"%s","category":"others","nickname":"nick"},
	 {"lua_path":"library/New_App/2/New_App.lua","sha256":"%s"},
	 {"lua_path":"library/Old_App/1/Old_App.lua","sha256":"%s"},
	 {"lua_path":"library/Bad_App/1/Bad_App.lua","sha256":"%s"}]}`,
		hex.EncodeToString(sum[:]), hex.EncodeToString(sum[:]), hex.EncodeToString(sum[:]), strings.Repeat("1", 64))
	ref := fmt.Sprintf("%04x%s refs/heads/main\n0000", 4+40+len(" refs/heads/main\n"), commit)
	raw := "raw.githubusercontent.com/o/r/" + commit + "/library/"
	gh := fakeGitHub{
		"github.com/o/r.git/info/refs": ref,
		raw + "index.json":             idx,
		raw + "New_App/1/New_App.lua":  luaA,
		raw + "New_App/2/New_App.lua":  luaA,
		raw + "Old_App/1/Old_App.lua":  luaA,
		raw + "Bad_App/1/Bad_App.lua":  "tampered",
	}
	return &library.Client{Loc: library.Location{Owner: "o", Repo: "r", Branch: "main", Dir: "library"}, HTTP: &http.Client{Transport: gh}}
}

type fakeFMC struct {
	specs     []fmc.Spec
	activated []string
	existing  []fmc.Detector
}

func (f *fakeFMC) Login() error          { return nil }
func (f *fakeFMC) ServerVersion() string { return "10.0.1" }
func (f *fakeFMC) Import(s fmc.Spec) (fmc.Result, error) {
	f.specs = append(f.specs, s)
	if s.AppName == "Old_App" {
		return fmc.Result{Status: "skipped", Message: "application already exists in FMC"}, nil
	}
	return fmc.Result{Status: "imported", UUID: "u-" + s.AppName, Category: s.Category, Message: "imported (Inactive)"}, nil
}
func (f *fakeFMC) Detectors(names map[string]bool) (map[string][]fmc.Detector, error) {
	out := map[string][]fmc.Detector{}
	for _, d := range f.existing {
		if names[strings.ToLower(d.Name)] {
			out[strings.ToLower(d.Name)] = append(out[strings.ToLower(d.Name)], d)
		}
	}
	return out, nil
}
func (f *fakeFMC) Activate(uuids []string, _ map[string]bool, _ func(string)) (map[string]bool, error) {
	f.activated = append(f.activated, uuids...)
	out := map[string]bool{}
	for _, u := range uuids {
		out[u] = true
	}
	return out, nil
}

func waitJob(t *testing.T, r *jobRunner) *Job {
	t.Helper()
	for i := 0; i < 200; i++ {
		if j := r.snapshot(); j.State != "running" {
			return j
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatal("job did not finish")
	return nil
}

func TestJobImportAndActivate(t *testing.T) {
	f := &fakeFMC{existing: []fmc.Detector{
		{UUID: "builtin", Name: "Old_App", Active: false, Editable: false},
		{UUID: "custom-old", Name: "Old_App", Active: false, Editable: true},
	}}
	r := &jobRunner{lib: testLibrary(), newClient: func(FMCLogin) (fmcAPI, error) { return f, nil }}
	_, err := r.start(FMCLogin{Host: "h"}, []Item{{"New_App", 2}, {"New_App", 1}, {"Old_App", 1}, {"Bad_App", 1}}, true)
	if err != nil {
		t.Fatal(err)
	}
	j := waitJob(t, r)
	if j.State != "done" || j.FMCVersion != "10.0.1" {
		t.Fatalf("job %+v", j)
	}
	want := []string{"imported", "skipped", "skipped", "error"}
	for i, w := range want {
		if j.Results[i].Status != w {
			t.Fatalf("result %d = %+v, want %s", i, j.Results[i], w)
		}
	}
	if !strings.Contains(j.Results[3].Message, "SHA256") {
		t.Fatalf("tampered Lua not refused: %+v", j.Results[3])
	}
	if s := f.specs[0]; s.Category != "others" || s.Risk != 2 || s.BusinessRelevance != 3 || s.Description != "NGFW shared Lua library v2 (-)" {
		t.Fatalf("defaults not applied: %+v", s)
	}
	if len(f.activated) != 2 || !contains(f.activated, "u-New_App") || !contains(f.activated, "custom-old") || contains(f.activated, "builtin") {
		t.Fatalf("activated %v", f.activated)
	}
	if a := j.Results[0].Active; a == nil || !*a || !strings.Contains(j.Results[0].Message, "(Active)") {
		t.Fatalf("new detector not reported active: %+v", j.Results[0])
	}
	if !strings.Contains(j.Results[2].Message, "activated the existing") {
		t.Fatalf("existing detector message: %+v", j.Results[2])
	}
}

func TestJobWithoutActivate(t *testing.T) {
	f := &fakeFMC{}
	r := &jobRunner{lib: testLibrary(), newClient: func(FMCLogin) (fmcAPI, error) { return f, nil }}
	r.start(FMCLogin{}, []Item{{"New_App", 1}}, false)
	j := waitJob(t, r)
	if j.Results[0].Status != "imported" || len(f.activated) != 0 || j.Results[0].Active != nil {
		t.Fatalf("%+v %v", j.Results[0], f.activated)
	}
}

func TestJobLoginFailure(t *testing.T) {
	r := &jobRunner{lib: testLibrary(), newClient: func(FMCLogin) (fmcAPI, error) { return nil, errors.New("FMC address is invalid") }}
	r.start(FMCLogin{}, []Item{{"New_App", 1}}, false)
	if j := waitJob(t, r); j.State != "failed" || j.Error == "" {
		t.Fatalf("%+v", j)
	}
}

func contains(list []string, v string) bool {
	for _, x := range list {
		if x == v {
			return true
		}
	}
	return false
}

func TestGuard(t *testing.T) {
	s := New(testLibrary(), filepath.Join(t.TempDir(), "s.json"))
	h := s.Handler("8790")
	do := func(method, host, path, token string) int {
		req := httptest.NewRequest(method, "http://"+host+path, strings.NewReader(`{"lang":"en"}`))
		if token != "" {
			req.Header.Set("X-Token", token)
		}
		w := httptest.NewRecorder()
		h.ServeHTTP(w, req)
		return w.Code
	}
	if c := do("GET", "evil.com:8790", "/", ""); c != 403 {
		t.Errorf("foreign Host allowed: %d", c)
	}
	if c := do("GET", "127.0.0.1:9999", "/", ""); c != 403 {
		t.Errorf("wrong port allowed: %d", c)
	}
	if c := do("POST", "127.0.0.1:8790", "/api/settings", ""); c != 403 {
		t.Errorf("API without token allowed: %d", c)
	}
	if c := do("POST", "127.0.0.1:8790", "/api/settings", s.token); c != 200 {
		t.Errorf("valid token rejected: %d", c)
	}
	if s.settings.load().Lang != "en" {
		t.Error("language not saved")
	}

	req := httptest.NewRequest("GET", "http://localhost:8790/", nil)
	w := httptest.NewRecorder()
	h.ServeHTTP(w, req)
	if w.Code != 200 || !strings.Contains(w.Body.String(), s.token) || strings.Contains(w.Body.String(), "__TOKEN__") {
		t.Fatalf("index did not embed token: %d", w.Code)
	}
	for _, p := range []string{"/static/app.js", "/static/style.css"} {
		if c := do("GET", "localhost:8790", p, ""); c != 200 {
			t.Errorf("%s = %d", p, c)
		}
	}
	if c := do("GET", "localhost:8790", "/api/library", s.token); c != 200 {
		t.Errorf("/api/library = %d", c)
	}
}

func TestPasswordNeverSaved(t *testing.T) {
	s := New(testLibrary(), filepath.Join(t.TempDir(), "s.json"))
	s.remember(FMCLogin{Host: "fmc", Username: "u", Password: "secret"})
	if st := s.settings.load(); st.Host != "fmc" || st.Username != "u" {
		t.Fatalf("%+v", st)
	}
	data, _ := os.ReadFile(s.settings.path)
	if strings.Contains(string(data), "secret") {
		t.Fatal("password written to disk")
	}
}

func TestSaveFMCSettings(t *testing.T) {
	s := New(testLibrary(), filepath.Join(t.TempDir(), "s.json"))
	h := s.Handler("8790")
	post := func(body string) int {
		req := httptest.NewRequest("POST", "http://127.0.0.1:8790/api/settings", strings.NewReader(body))
		req.Header.Set("X-Token", s.token)
		w := httptest.NewRecorder()
		h.ServeHTTP(w, req)
		return w.Code
	}
	if c := post(`{"lang":"en"}`); c != 200 {
		t.Fatalf("lang = %d", c)
	}
	if c := post(`{"host":" 10.1.1.1 ","username":"ops","verify_tls":true,"password":"secret"}`); c != 200 {
		t.Fatalf("save = %d", c)
	}
	st := s.settings.load()
	if st.Host != "10.1.1.1" || st.Username != "ops" || !st.VerifyTLS || st.Lang != "en" {
		t.Fatalf("%+v", st)
	}
	if data, _ := os.ReadFile(s.settings.path); strings.Contains(string(data), "secret") {
		t.Fatal("password written to disk")
	}
	if c := post(`{"host":"bad host!"}`); c != 400 {
		t.Errorf("bad host accepted: %d", c)
	}
	if c := post(`{"lang":"fr"}`); c != 400 {
		t.Errorf("bad lang accepted: %d", c)
	}
}
