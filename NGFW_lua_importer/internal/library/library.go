// Package library reads the maintainer-curated Lua detector library from GitHub.
//
// Access is anonymous and read-only: the latest commit of the branch is
// resolved through GitHub's Git smart-HTTP ref advertisement, and index.json
// plus every Lua file are read at that immutable commit (raw.githubusercontent.com,
// falling back to the cdn.jsdelivr.net mirror). Each Lua is checked against the
// SHA256 recorded in the index before it is handed out.
package library

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	maxIndexBytes = 8 << 20
	maxLuaBytes   = 256 << 10
	cacheTTL      = 60 * time.Second
)

var (
	nameRE   = regexp.MustCompile(`^[A-Za-z0-9_.-]{1,100}$`)
	branchRE = regexp.MustCompile(`^[A-Za-z0-9_./-]{1,200}$`)
	dirRE    = regexp.MustCompile(`^[A-Za-z0-9_-]{1,64}$`)
	shaRE    = regexp.MustCompile(`^[0-9a-f]{64}$`)
	commitRE = regexp.MustCompile(`^[0-9a-f]{40}$`)
)

// ErrNotFound means every source answered 404 (the library has no index yet).
var ErrNotFound = errors.New("library index not found")

// Location identifies the GitHub repository that hosts the library.
type Location struct {
	Owner          string
	Repo           string
	Branch         string
	Dir            string
	MirrorFallback bool
}

func (l Location) Validate() error {
	if !nameRE.MatchString(l.Owner) || !nameRE.MatchString(l.Repo) {
		return errors.New("library GitHub owner/repository is invalid")
	}
	if !branchRE.MatchString(l.Branch) || !dirRE.MatchString(l.Dir) {
		return errors.New("library branch or directory is invalid")
	}
	return nil
}

// RepoURL is the human-facing GitHub page of the library directory.
func (l Location) RepoURL() string {
	return fmt.Sprintf("https://github.com/%s/%s/tree/%s/%s", l.Owner, l.Repo, l.Branch, l.Dir)
}

func (l Location) luaPathRE() *regexp.Regexp {
	d := regexp.QuoteMeta(l.Dir)
	return regexp.MustCompile(`^` + d + `/([A-Za-z_]{1,15})/([1-9][0-9]{0,3})/([A-Za-z_]{1,15})\.lua$`)
}

type source struct{ name, url string }

func (l Location) sources(path, ref string) []source {
	if ref == "" {
		ref = l.Branch
	}
	out := []source{{"github", fmt.Sprintf("https://raw.githubusercontent.com/%s/%s/%s/%s", l.Owner, l.Repo, ref, path)}}
	if l.MirrorFallback {
		out = append(out, source{"jsdelivr", fmt.Sprintf("https://cdn.jsdelivr.net/gh/%s/%s@%s/%s", l.Owner, l.Repo, ref, path)})
	}
	return out
}

// Entry is one published detector version.
type Entry struct {
	AppName           string   `json:"app_name"`
	Version           int      `json:"version"`
	LuaPath           string   `json:"lua_path"`
	SHA256            string   `json:"sha256"`
	Size              int      `json:"size"`
	Nickname          string   `json:"nickname"`
	FMCVersion        string   `json:"fmc_version"`
	ToolVersion       string   `json:"tool_version"`
	Category          string   `json:"category"`
	Risk              int      `json:"risk"`
	BusinessRelevance int      `json:"business_relevance"`
	Notes             string   `json:"notes"`
	ReviewNote        string   `json:"review_note"`
	PublishedAt       string   `json:"published_at"`
	HostPatterns      []string `json:"host_patterns"`
}

// Snapshot is the parsed index plus where it came from.
type Snapshot struct {
	Entries []Entry `json:"entries"`
	Source  string  `json:"source"`
	Commit  string  `json:"commit"`
}

// Client is an anonymous, read-only library reader with a short index cache.
type Client struct {
	Loc  Location
	HTTP *http.Client

	mu      sync.Mutex
	cached  *Snapshot
	fetched time.Time
}

func clip(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n]
}

func str(v any) string {
	switch t := v.(type) {
	case string:
		return t
	case float64:
		return strconv.FormatFloat(t, 'f', -1, 64)
	}
	return ""
}

func level(v any) int {
	if f, ok := v.(float64); ok && f == float64(int(f)) && f >= 1 && f <= 5 {
		return int(f)
	}
	return 0
}

// ParseIndex validates index.json and drops entries that do not point inside the library.
func ParseIndex(data []byte, loc Location) ([]Entry, error) {
	var payload struct {
		Entries []map[string]any `json:"entries"`
	}
	if err := json.Unmarshal(data, &payload); err != nil {
		return nil, errors.New("library index.json is not valid JSON")
	}
	if payload.Entries == nil {
		return nil, errors.New("library index.json has no entries list")
	}
	re := loc.luaPathRE()
	var out []Entry
	for _, raw := range payload.Entries {
		path := str(raw["lua_path"])
		m := re.FindStringSubmatch(path)
		sha := strings.ToLower(clip(str(raw["sha256"]), 64))
		if m == nil || m[1] != m[3] || !shaRE.MatchString(sha) {
			continue
		}
		ver, _ := strconv.Atoi(m[2])
		size := 0
		if f, ok := raw["size"].(float64); ok && f > 0 {
			size = int(f)
		}
		e := Entry{
			AppName: m[1], Version: ver, LuaPath: path, SHA256: sha, Size: size,
			Nickname:          clip(str(raw["nickname"]), 32),
			FMCVersion:        clip(str(raw["fmc_version"]), 64),
			ToolVersion:       clip(str(raw["tool_version"]), 32),
			Category:          clip(str(raw["category"]), 64),
			Risk:              level(raw["risk"]),
			BusinessRelevance: level(raw["business_relevance"]),
			Notes:             clip(str(raw["notes"]), 2000),
			ReviewNote:        clip(str(raw["review_note"]), 2000),
			PublishedAt:       clip(str(raw["published_at"]), 40),
		}
		if e.Nickname == "" {
			e.Nickname = "-"
		}
		if hp, ok := raw["host_patterns"].([]any); ok {
			for i, p := range hp {
				if i >= 200 {
					break
				}
				e.HostPatterns = append(e.HostPatterns, clip(str(p), 255))
			}
		}
		out = append(out, e)
	}
	sort.Slice(out, func(i, j int) bool {
		a, b := strings.ToLower(out[i].AppName), strings.ToLower(out[j].AppName)
		if a != b {
			return a < b
		}
		return out[i].Version > out[j].Version
	})
	return out, nil
}

// ParseBranchHead extracts the commit of refs/heads/<branch> from a Git pkt-line ref advertisement.
func ParseBranchHead(data []byte, branch string) (string, error) {
	target := []byte("refs/heads/" + branch)
	for off := 0; off < len(data); {
		if off+4 > len(data) {
			return "", errors.New("GitHub returned a truncated Git ref advertisement")
		}
		n, err := strconv.ParseUint(string(data[off:off+4]), 16, 16)
		if err != nil {
			return "", errors.New("GitHub returned an invalid Git ref advertisement")
		}
		if n == 0 {
			off += 4
			continue
		}
		if n < 4 || off+int(n) > len(data) {
			return "", errors.New("GitHub returned a truncated Git ref advertisement")
		}
		pkt := data[off+4 : off+int(n)]
		off += int(n)
		pkt = bytes.SplitN(pkt, []byte{0}, 2)[0]
		fields := bytes.SplitN(bytes.TrimRight(pkt, "\n"), []byte(" "), 2)
		if len(fields) == 2 && bytes.Equal(fields[1], target) {
			if !commitRE.Match(fields[0]) {
				return "", errors.New("GitHub returned an invalid branch commit")
			}
			return string(fields[0]), nil
		}
	}
	return "", errors.New("the configured branch was not advertised by GitHub")
}

func (c *Client) get(url string, limit int64, noCache bool) ([]byte, int, error) {
	req, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return nil, 0, err
	}
	req.Header.Set("User-Agent", "ngfw-lua-importer")
	if noCache {
		req.Header.Set("Cache-Control", "no-cache")
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, 0, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, limit+1))
	if err != nil {
		return nil, resp.StatusCode, err
	}
	if int64(len(body)) > limit {
		return nil, resp.StatusCode, errors.New("response too large")
	}
	return body, resp.StatusCode, nil
}

func (c *Client) branchHead() (string, error) {
	url := fmt.Sprintf("https://github.com/%s/%s.git/info/refs?service=git-upload-pack", c.Loc.Owner, c.Loc.Repo)
	body, status, err := c.get(url, 4<<20, true)
	if err != nil {
		return "", fmt.Errorf("github-head: %v", err)
	}
	if status != http.StatusOK {
		return "", fmt.Errorf("github-head: HTTP %d", status)
	}
	return ParseBranchHead(body, c.Loc.Branch)
}

func (c *Client) fetch(path, ref string, limit int64, noCache bool) ([]byte, string, error) {
	var errs []string
	all404 := true
	for _, s := range c.Loc.sources(path, ref) {
		url := s.url
		if noCache {
			url += fmt.Sprintf("?t=%d", time.Now().UnixNano())
		}
		body, status, err := c.get(url, limit, noCache)
		if err == nil && status == http.StatusOK {
			name := s.name
			if ref != "" {
				name += "-commit"
			}
			return body, name, nil
		}
		if err != nil {
			errs = append(errs, s.name+": "+err.Error())
			all404 = false
		} else {
			errs = append(errs, fmt.Sprintf("%s: HTTP %d", s.name, status))
			all404 = all404 && status == http.StatusNotFound
		}
	}
	msg := "library is not reachable (" + strings.Join(errs, "; ") + ")"
	if all404 {
		return nil, "", fmt.Errorf("%w: %s", ErrNotFound, msg)
	}
	return nil, "", errors.New(msg)
}

// Snapshot returns the cached index, refreshing it when stale or when force is set.
func (c *Client) Snapshot(force bool) (*Snapshot, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if !force && c.cached != nil && time.Since(c.fetched) < cacheTTL {
		return c.cached, nil
	}
	indexPath := c.Loc.Dir + "/index.json"
	commit, headErr := c.branchHead()
	var data []byte
	var src string
	var err error
	if headErr == nil {
		data, src, err = c.fetch(indexPath, commit, maxIndexBytes, false)
	}
	if headErr != nil || (err != nil && !errors.Is(err, ErrNotFound)) {
		// Branch caches may lag behind the latest commit by a few minutes.
		commit = ""
		data, src, err = c.fetch(indexPath, "", maxIndexBytes, force)
		if err != nil && headErr != nil {
			err = fmt.Errorf("%v; %w", headErr, err)
		}
	}
	snap := &Snapshot{Commit: commit, Source: src}
	switch {
	case errors.Is(err, ErrNotFound):
		snap.Source, snap.Commit, snap.Entries = "empty", "", []Entry{}
	case err != nil:
		return nil, err
	default:
		if snap.Entries, err = ParseIndex(data, c.Loc); err != nil {
			return nil, err
		}
	}
	c.cached, c.fetched = snap, time.Now()
	return snap, nil
}

// Find looks an entry up, refreshing the index once if it is missing from the cache.
func (c *Client) Find(app string, version int) (Entry, string, error) {
	for _, force := range []bool{false, true} {
		snap, err := c.Snapshot(force)
		if err != nil {
			return Entry{}, "", err
		}
		for _, e := range snap.Entries {
			if e.AppName == app && e.Version == version {
				return e, snap.Commit, nil
			}
		}
	}
	return Entry{}, "", fmt.Errorf("%s v%d is not in the library index", app, version)
}

// ReadLua downloads a detector and refuses it when the SHA256 does not match the index.
func (c *Client) ReadLua(app string, version int) ([]byte, Entry, error) {
	e, commit, err := c.Find(app, version)
	if err != nil {
		return nil, e, err
	}
	data, _, err := c.fetch(e.LuaPath, commit, maxLuaBytes, false)
	if err != nil {
		return nil, e, err
	}
	sum := sha256.Sum256(data)
	if hex.EncodeToString(sum[:]) != e.SHA256 {
		return nil, e, errors.New("SHA256 mismatch with the library index; refused")
	}
	return data, e, nil
}
