package library

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net/http"
	"strings"
	"testing"
)

var loc = Location{Owner: "o", Repo: "r", Branch: "main", Dir: "library", MirrorFallback: true}

func pkt(s string) string { return fmt.Sprintf("%04x%s", len(s)+4, s) }

func TestParseBranchHead(t *testing.T) {
	commit := strings.Repeat("a", 40)
	adv := pkt("# service=git-upload-pack\n") + "0000" +
		pkt(strings.Repeat("b", 40)+" HEAD\x00caps\n") +
		pkt(commit+" refs/heads/main\n") + "0000"
	got, err := ParseBranchHead([]byte(adv), "main")
	if err != nil || got != commit {
		t.Fatalf("got %q %v", got, err)
	}
	if _, err := ParseBranchHead([]byte(adv), "dev"); err == nil {
		t.Fatal("missing branch accepted")
	}
	if _, err := ParseBranchHead([]byte("00zz"), "main"); err == nil {
		t.Fatal("garbage accepted")
	}
}

func TestParseIndexFiltersUnsafePaths(t *testing.T) {
	sha := strings.Repeat("c", 64)
	idx := fmt.Sprintf(`{"entries":[
	 {"lua_path":"library/Good_App/2/Good_App.lua","sha256":"%[1]s","risk":4,"business_relevance":9,"category":"others","host_patterns":["a.com"]},
	 {"lua_path":"library/Good_App/1/Good_App.lua","sha256":"%[1]s"},
	 {"lua_path":"library/../etc/1/x.lua","sha256":"%[1]s"},
	 {"lua_path":"library/A/1/B.lua","sha256":"%[1]s"},
	 {"lua_path":"library/C/1/C.lua","sha256":"short"}]}`, sha)
	out, err := ParseIndex([]byte(idx), loc)
	if err != nil {
		t.Fatal(err)
	}
	if len(out) != 2 || out[0].Version != 2 || out[0].Risk != 4 || out[0].BusinessRelevance != 0 || out[0].Nickname != "-" {
		t.Fatalf("unexpected entries %+v", out)
	}
	if _, err := ParseIndex([]byte(`{}`), loc); err == nil {
		t.Fatal("index without entries accepted")
	}
}

type fakeGitHub struct {
	files map[string]string
	hits  []string
}

func (f *fakeGitHub) RoundTrip(r *http.Request) (*http.Response, error) {
	u := r.URL.Host + r.URL.Path
	f.hits = append(f.hits, u)
	body, ok := f.files[u]
	status := 200
	if !ok {
		status, body = 404, "nope"
	}
	return &http.Response{StatusCode: status, Body: io.NopCloser(strings.NewReader(body)), Header: http.Header{}, Request: r}, nil
}

func TestReadLuaVerifiesSHA(t *testing.T) {
	commit := strings.Repeat("d", 40)
	lua := "-- lua\n"
	sum := sha256.Sum256([]byte(lua))
	good := hex.EncodeToString(sum[:])
	idx := fmt.Sprintf(`{"entries":[{"lua_path":"library/Good/1/Good.lua","sha256":"%s"},{"lua_path":"library/Evil/1/Evil.lua","sha256":"%s"}]}`, good, strings.Repeat("0", 64))
	gh := &fakeGitHub{files: map[string]string{
		"github.com/o/r.git/info/refs":                                         pkt(commit+" refs/heads/main\n") + "0000",
		"raw.githubusercontent.com/o/r/" + commit + "/library/index.json":      idx,
		"raw.githubusercontent.com/o/r/" + commit + "/library/Good/1/Good.lua": lua,
		// GitHub raw is "down" for Evil; the mirror serves tampered content.
		"cdn.jsdelivr.net/gh/o/r@" + commit + "/library/Evil/1/Evil.lua": "evil",
	}}
	c := &Client{Loc: loc, HTTP: &http.Client{Transport: gh}}
	snap, err := c.Snapshot(false)
	if err != nil || len(snap.Entries) != 2 || snap.Commit != commit || snap.Source != "github-commit" {
		t.Fatalf("snapshot %+v %v", snap, err)
	}
	data, _, err := c.ReadLua("Good", 1)
	if err != nil || string(data) != lua {
		t.Fatalf("ReadLua good: %q %v", data, err)
	}
	if _, _, err := c.ReadLua("Evil", 1); err == nil || !strings.Contains(err.Error(), "SHA256") {
		t.Fatalf("tampered Lua accepted: %v", err)
	}
	if _, _, err := c.ReadLua("Missing", 1); err == nil {
		t.Fatal("missing entry accepted")
	}
}

func TestEmptyLibrary(t *testing.T) {
	gh := &fakeGitHub{files: map[string]string{}}
	c := &Client{Loc: loc, HTTP: &http.Client{Transport: gh}}
	snap, err := c.Snapshot(true)
	if err != nil || snap.Source != "empty" || len(snap.Entries) != 0 {
		t.Fatalf("%+v %v", snap, err)
	}
}

func TestLocationValidate(t *testing.T) {
	if (Location{Owner: "o", Repo: "r", Branch: "main", Dir: "library"}).Validate() != nil {
		t.Fatal("valid location rejected")
	}
	if (Location{Owner: "o/../x", Repo: "r", Branch: "main", Dir: "library"}).Validate() == nil {
		t.Fatal("bad owner accepted")
	}
}
