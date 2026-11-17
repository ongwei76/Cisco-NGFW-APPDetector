// Package fmc uploads custom Lua application detectors to Cisco Secure Firewall
// Management Center (FMC).
//
// FMC has no public REST API for custom application detectors, so this client
// replays the calls the FMC Web UI makes on Policies > Application Detectors
// (verified on FMC 10.0.1):
//
//  1. POST /login.cgi (form login) sets the CGISESSID session cookie.
//  2. GET /ddd/ yields the per-session CSRF token (sf_action_id).
//  3. pjb.cgi SF::Cache::RNADetector::saveApp creates the application with its
//     category, risk and business relevance.
//  4. pjb.cgi setDetector("new") creates an empty Advanced (protocol=custom) detector.
//  5. POST /RNADetector/detectors.cgi uploads the Lua for that detector.
//  6. pjb.cgi setDetector("save") stores it; the stored Lua is compared with the upload.
//  7. Optionally pjb.cgi activateDetectors activates the new detectors.
//
// A failed upload deletes the half-created detector (which also removes the
// custom application). FMC pushes activation to managed devices itself; no
// deployment is needed (Snort 2 devices restart Snort, Snort 3 devices do not).
package fmc

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"regexp"
	"strings"
	"time"
)

var (
	actionIDRE     = regexp.MustCompile(`sf_action_id\s*=\s*"([0-9a-fA-F]+)"`)
	uploadResultRE = regexp.MustCompile(`FILENAME=[^!]*!!(SUCCESS|ERROR)=([^!]*)`)
	tagRE          = regexp.MustCompile(`<[^>]+>`)
	buildRE        = regexp.MustCompile(`"fmcBuild"\s*:\s*"([0-9.]+)-([0-9]+)"`)
	titleVerRE     = regexp.MustCompile(`Management Center[^<]*?\s([0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?) Build ([0-9]+)`)
	hostRE         = regexp.MustCompile(`^[A-Za-z0-9.\-:\[\]]{1,255}$`)
)

// Error is an FMC-side rejection with a user-readable message.
type Error struct{ Msg string }

func (e *Error) Error() string { return e.Msg }

func fail(format string, a ...any) error { return &Error{fmt.Sprintf(format, a...)} }

// Spec describes one detector to import.
type Spec struct {
	AppName           string
	Lua               []byte
	Description       string
	Category          string
	Risk              int
	BusinessRelevance int
}

// Result is the outcome of importing one detector.
type Result struct {
	Status        string `json:"status"` // imported | skipped
	UUID          string `json:"uuid,omitempty"`
	AppID         int    `json:"app_id,omitempty"`
	Category      string `json:"category,omitempty"`
	CategoryExact bool   `json:"category_exact"`
	Message       string `json:"message"`
}

// Detector is a row of the FMC detector list.
type Detector struct {
	UUID     string
	Name     string
	Active   bool
	Editable bool
}

// Client speaks the FMC Web UI endpoints with one CGISESSID session.
type Client struct {
	Base     string
	user     string
	password string
	http     *http.Client
	actionID string
	version  string
	apps     map[string]bool
	cats     map[string]category
	Timeout  time.Duration
	// PollEvery is the activation status polling interval.
	PollEvery time.Duration
}

type category struct {
	id   int
	name string
}

// NormalizeHost accepts "10.0.0.1", "fmc.example.com:8443" or a pasted https:// URL.
func NormalizeHost(host string) (string, error) {
	h := strings.TrimSpace(host)
	if strings.Contains(h, "://") {
		u, err := url.Parse(h)
		if err != nil {
			return "", errors.New("FMC address is invalid")
		}
		h = u.Host
	}
	h = strings.TrimRight(h, "/")
	if !hostRE.MatchString(h) {
		return "", errors.New("FMC address is invalid")
	}
	return h, nil
}

// New returns a client; FMC is contacted directly (no proxy).
func New(host, user, password string, verifyTLS bool) (*Client, error) {
	h, err := NormalizeHost(host)
	if err != nil {
		return nil, err
	}
	if user == "" || password == "" {
		return nil, errors.New("FMC username and password are required")
	}
	jar, _ := cookiejar.New(nil)
	transport := &http.Transport{
		Proxy:               nil,
		TLSClientConfig:     &tls.Config{InsecureSkipVerify: !verifyTLS}, //nolint:gosec // FMC usually has a self-signed certificate; user can enable verification.
		TLSHandshakeTimeout: 15 * time.Second,
	}
	return &Client{
		Base:      "https://" + h,
		user:      user,
		password:  password,
		Timeout:   45 * time.Second,
		PollEvery: 15 * time.Second,
		http: &http.Client{
			Jar:       jar,
			Transport: transport,
			CheckRedirect: func(*http.Request, []*http.Request) error {
				return http.ErrUseLastResponse
			},
		},
	}, nil
}

func (c *Client) do(ctx context.Context, req *http.Request) (*http.Response, []byte, error) {
	req = req.WithContext(ctx)
	req.Header.Set("User-Agent", "Mozilla/5.0 ngfw-lua-importer")
	resp, err := c.http.Do(req)
	if err != nil {
		return nil, nil, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 64<<20))
	return resp, body, err
}

func (c *Client) ctx(d time.Duration) (context.Context, context.CancelFunc) {
	if d == 0 {
		d = c.Timeout
	}
	return context.WithTimeout(context.Background(), d)
}

// Login authenticates and fetches the CSRF token.
func (c *Client) Login() error {
	ctx, cancel := c.ctx(0)
	defer cancel()
	req, _ := http.NewRequest(http.MethodGet, c.Base+"/ui/login", nil)
	if _, _, err := c.do(ctx, req); err != nil {
		return fmt.Errorf("cannot reach FMC %s: %v", c.Base, err)
	}
	form := url.Values{"username": {c.user}, "password": {c.password}}
	req, _ = http.NewRequest(http.MethodPost, c.Base+"/login.cgi", strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Referer", c.Base+"/ui/login")
	resp, _, err := c.do(ctx, req)
	if err != nil {
		return fmt.Errorf("FMC login failed: %v", err)
	}
	u, _ := url.Parse(c.Base)
	hasSession := false
	for _, ck := range c.http.Jar.Cookies(u) {
		if ck.Name == "CGISESSID" && ck.Value != "" {
			hasSession = true
		}
	}
	if (resp.StatusCode != 200 && resp.StatusCode != 302) || !hasSession {
		return fail("FMC login failed (HTTP %d): check the username and password", resp.StatusCode)
	}
	return c.connect()
}

func (c *Client) connect() error {
	ctx, cancel := c.ctx(0)
	defer cancel()
	req, _ := http.NewRequest(http.MethodGet, c.Base+"/ddd/", nil)
	resp, body, err := c.do(ctx, req)
	if err != nil {
		return fmt.Errorf("FMC Web UI session: %v", err)
	}
	if m := actionIDRE.FindSubmatch(body); resp.StatusCode == 200 && m != nil {
		c.actionID = string(m[1])
		c.version = parseVersion(body)
		return nil
	}
	return fail("FMC Web UI session could not be established (HTTP %d); this FMC version may not be compatible", resp.StatusCode)
}

// errNoData is returned when pjb.cgi answers without data, which happens when the
// Web UI session was logged out (for example by a REST API login with the same account).
func errNoData(fn string) error {
	return fail("%s: FMC returned no data; the FMC Web UI session was logged out (FMC allows one Web UI session per account; was the same account used elsewhere?), please retry", fn)
}

func clipErr(err error) string {
	msg := err.Error()
	if len(msg) > 160 {
		msg = msg[:160]
	}
	return msg
}

func shortName(fn string) string {
	if i := strings.LastIndex(fn, "::"); i >= 0 {
		return fn[i+2:]
	}
	return fn
}

// Call invokes one pjb.cgi function and returns its "data" member.
func (c *Client) Call(fn string, params any, page string, timeout time.Duration) (json.RawMessage, error) {
	if c.actionID == "" {
		if err := c.connect(); err != nil {
			return nil, err
		}
	}
	if page == "" {
		page = "DetectorList"
	}
	p, err := json.Marshal(params)
	if err != nil {
		return nil, err
	}
	form := url.Values{
		"function": {fn}, "parameters": {string(p)}, "get_all_errors": {"1"},
		"sf_action_id": {c.actionID}, "ss": {page},
	}
	ctx, cancel := c.ctx(timeout)
	defer cancel()
	req, _ := http.NewRequest(http.MethodPost, c.Base+"/pjb.cgi", strings.NewReader(form.Encode()))
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Referer", c.Base+"/ddd/")
	resp, body, err := c.do(ctx, req)
	if err != nil {
		return nil, err
	}
	var payload struct {
		Data  json.RawMessage `json:"data"`
		Error json.RawMessage `json:"error"`
	}
	if json.Unmarshal(body, &payload) != nil {
		return nil, fail("%s: unexpected FMC response (HTTP %d)", shortName(fn), resp.StatusCode)
	}
	if len(payload.Error) > 0 && string(payload.Error) != "null" && string(payload.Error) != "false" && string(payload.Error) != `""` {
		var e struct {
			Text string `json:"text"`
		}
		msg := string(payload.Error)
		if json.Unmarshal(payload.Error, &e) == nil && e.Text != "" {
			msg = e.Text
		}
		return nil, fail("%s: %s", shortName(fn), msg)
	}
	return payload.Data, nil
}

// readCall runs a read-only pjb.cgi function and logs in again once when FMC
// dropped the Web UI session (FMC keeps one Web UI session per account).
func (c *Client) readCall(fn string, params any, timeout time.Duration) (json.RawMessage, error) {
	raw, err := c.Call(fn, params, "", timeout)
	if err == nil && (len(raw) == 0 || string(raw) == "null") {
		if lerr := c.Login(); lerr != nil {
			return nil, lerr
		}
		raw, err = c.Call(fn, params, "", timeout)
	}
	if err == nil && (len(raw) == 0 || string(raw) == "null") {
		return nil, errNoData(shortName(fn))
	}
	return raw, err
}

func (c *Client) loadCatalog() error {
	raw, err := c.readCall("SF::Cache::RNADetector::getFilterList", []any{}, 0)
	if err != nil {
		return err
	}
	var data struct {
		Apps struct {
			Applications []struct {
				AppName any `json:"appName"`
			} `json:"Applications"`
		} `json:"apps"`
		Filters []struct {
			Key  string          `json:"key"`
			List json.RawMessage `json:"list"`
		} `json:"filters"`
	}
	if err := json.Unmarshal(raw, &data); err != nil {
		return fail("getFilterList: unexpected FMC response (%s); retry, or this FMC version may not be compatible", clipErr(err))
	}
	c.apps = map[string]bool{}
	for _, a := range data.Apps.Applications {
		if s := fmt.Sprint(a.AppName); a.AppName != nil && s != "" {
			c.apps[strings.ToLower(s)] = true
		}
	}
	c.cats = map[string]category{}
	for _, f := range data.Filters {
		if f.Key != "category" {
			continue
		}
		// Only the category list is used; other filter groups carry non-string names.
		var list []struct {
			ID   any `json:"id"`
			Name any `json:"name"`
		}
		if json.Unmarshal(f.List, &list) != nil {
			continue
		}
		for _, it := range list {
			var id int
			name := fmt.Sprint(it.Name)
			if _, err := fmt.Sscan(fmt.Sprint(it.ID), &id); err == nil && it.Name != nil && name != "" {
				c.cats[strings.ToLower(name)] = category{id, name}
			}
		}
	}
	if len(c.cats) == 0 {
		return fail("FMC did not return its application categories")
	}
	return nil
}

// AppExists reports whether FMC already has an application with this name.
func (c *Client) AppExists(name string) (bool, error) {
	if c.apps == nil {
		if err := c.loadCatalog(); err != nil {
			return false, err
		}
	}
	return c.apps[strings.ToLower(name)], nil
}

func (c *Client) resolveCategory(name string) (category, bool, error) {
	if c.cats == nil {
		if err := c.loadCatalog(); err != nil {
			return category{}, false, err
		}
	}
	if cat, ok := c.cats[strings.ToLower(strings.TrimSpace(name))]; ok {
		return cat, true, nil
	}
	if cat, ok := c.cats["others"]; ok {
		return cat, false, nil
	}
	for _, cat := range c.cats {
		return cat, false, nil
	}
	return category{}, false, fail("no FMC category available")
}

// Import creates the application and its Advanced detector with the Lua (Inactive).
func (c *Client) Import(s Spec) (Result, error) {
	exists, err := c.AppExists(s.AppName)
	if err != nil {
		return Result{}, err
	}
	if exists {
		return Result{Status: "skipped", Message: "application already exists in FMC"}, nil
	}
	cat, exact, err := c.resolveCategory(s.Category)
	if err != nil {
		return Result{}, err
	}
	raw, err := c.Call("SF::Cache::RNADetector::saveApp", []any{map[string]any{
		"appName": s.AppName, "appId": -1, "risk_index": s.Risk, "productivity_index": s.BusinessRelevance,
		"appDescription": s.Description,
		"categories":     []any{map[string]any{"tagId": cat.id, "tagType": "category", "tagName": cat.name}},
		"tags":           []any{}, "isDecryptedOnlyDetector": 0,
	}}, "", 0)
	if err != nil {
		return Result{}, err
	}
	var app struct {
		AppID any `json:"appId"`
	}
	var appID int
	if len(raw) == 0 || string(raw) == "null" {
		return Result{}, errNoData("saveApp")
	}
	if json.Unmarshal(raw, &app) != nil || app.AppID == nil {
		return Result{}, fail("saveApp: FMC did not return an application id")
	}
	if _, err := fmt.Sscan(fmt.Sprint(app.AppID), &appID); err != nil {
		return Result{}, fail("saveApp: FMC did not return an application id")
	}
	c.apps[strings.ToLower(s.AppName)] = true

	orphan := fmt.Sprintf("remove the empty application %s in FMC before retrying", s.AppName)
	raw, err = c.Call("SF::Cache::RNADetector::setDetector", []any{"new", nil, map[string]any{
		"name": s.AppName, "domainName": "", "viewable": 1, "editable": 1, "active": 0,
		"clientServer": "", "patterns": []any{}, "appId": appID, "pcaps": map[string]any{},
		"description": s.Description, "protocol": "custom", "lua": 0,
	}}, "", 0)
	if err != nil {
		return Result{}, fail("%v; %s", err, orphan)
	}
	var created struct {
		Detector struct {
			UUID string `json:"uuid"`
		} `json:"detector"`
	}
	_ = json.Unmarshal(raw, &created)
	if created.Detector.UUID == "" {
		return Result{}, fail("setDetector: no detector was created; %s", orphan)
	}
	uuid := created.Detector.UUID
	if err := c.uploadAndSave(s, uuid, appID); err != nil {
		c.rollback(uuid)
		return Result{}, err
	}
	msg := "imported (Inactive)"
	if !exact {
		msg = fmt.Sprintf("imported (Inactive); category %q not found on this FMC, used %q", s.Category, cat.name)
	}
	return Result{Status: "imported", UUID: uuid, AppID: appID, Category: cat.name, CategoryExact: exact, Message: msg}, nil
}

// Comparable drops CR and non-printable/non-ASCII bytes so FMC re-encoding does not matter.
func Comparable(lua []byte) string {
	lua = bytes.ReplaceAll(lua, []byte("\r\n"), []byte("\n"))
	var b strings.Builder
	for _, ch := range lua {
		if ch == '\n' || ch == '\t' || (ch >= 0x20 && ch <= 0x7e) {
			b.WriteByte(ch)
		}
	}
	return strings.TrimSpace(b.String())
}

func (c *Client) uploadAndSave(s Spec, uuid string, appID int) error {
	if _, err := c.Call("SF::Cache::RNADetector::initDetectorEditorForAllApps", []any{uuid}, "DetectorEditor", 0); err != nil {
		return err
	}
	var buf bytes.Buffer
	mw := multipart.NewWriter(&buf)
	_ = mw.WriteField("sf_action_id", c.actionID)
	_ = mw.WriteField("detector_uuid", uuid)
	fw, _ := mw.CreateFormFile("lua_upload", s.AppName+".lua")
	_, _ = fw.Write(s.Lua)
	_ = mw.Close()
	ctx, cancel := c.ctx(0)
	defer cancel()
	req, _ := http.NewRequest(http.MethodPost, c.Base+"/RNADetector/detectors.cgi", &buf)
	req.Header.Set("Content-Type", mw.FormDataContentType())
	req.Header.Set("Referer", c.Base+"/ddd/")
	resp, body, err := c.do(ctx, req)
	if err != nil {
		return fmt.Errorf("Lua upload: %v", err)
	}
	m := uploadResultRE.FindSubmatch(body)
	if m == nil || string(m[1]) != "SUCCESS" {
		reason := fmt.Sprintf("HTTP %d", resp.StatusCode)
		if m != nil {
			reason = strings.Join(strings.Fields(tagRE.ReplaceAllString(string(m[2]), " ")), " ")
			reason = strings.Trim(reason, " -")
			if len(reason) > 300 {
				reason = reason[:300]
			}
			if reason == "" {
				reason = "no reason given"
			}
		}
		return fail("Lua upload rejected by FMC: %s", reason)
	}
	raw, err := c.Call("SF::Cache::RNADetector::setDetector", []any{"save", uuid, map[string]any{
		"service_name": s.AppName, "viewable": 1, "clientServer": "", "protocol": "custom",
		"service_id": appID, "patterns": []any{}, "active": 0, "appId": appID, "lua": 1,
		"description": s.Description, "subtype": 5, "ports": "", "pcaps": map[string]any{},
		"editable": 1, "name": s.AppName, "domainName": "",
	}}, "DetectorEditor", 0)
	if err != nil {
		return err
	}
	var saved struct {
		Detector struct {
			Data struct {
				Lua any `json:"lua"`
			} `json:"data"`
		} `json:"detector"`
	}
	_ = json.Unmarshal(raw, &saved)
	stored, ok := saved.Detector.Data.Lua.(string)
	if !ok || !strings.Contains(Comparable([]byte(stored)), Comparable(s.Lua)) {
		return fail("FMC saved the detector without the uploaded Lua")
	}
	return nil
}

func (c *Client) rollback(uuid string) {
	_, _ = c.Call("SF::Cache::RNADetector::deleteDetectors", []any{[]string{uuid}}, "", 2*time.Minute)
	c.apps = nil
}

// Detectors returns the FMC detectors whose name is in names (case-insensitive).
func (c *Client) Detectors(names map[string]bool) (map[string][]Detector, error) {
	out := map[string][]Detector{}
	for off, total := 0, 1; off < total; off += 2000 {
		raw, err := c.readCall("SF::Cache::RNADetector::getDetectorList",
			[]any{[]any{}, map[string]any{"column": nil, "ascending": 0}, off, 2000}, 2*time.Minute)
		if err != nil {
			return nil, err
		}
		var page struct {
			TotalRows int `json:"totalRows"`
			Detectors []struct {
				UUID string `json:"uuid"`
				Data struct {
					Name     string `json:"name"`
					Active   any    `json:"active"`
					Editable any    `json:"editable"`
				} `json:"data"`
			} `json:"detectors"`
		}
		if err := json.Unmarshal(raw, &page); err != nil {
			return nil, fail("getDetectorList: unexpected FMC response")
		}
		total = page.TotalRows
		for _, d := range page.Detectors {
			key := strings.ToLower(d.Data.Name)
			if names[key] {
				out[key] = append(out[key], Detector{
					UUID: d.UUID, Name: d.Data.Name,
					Active: fmt.Sprint(d.Data.Active) == "1", Editable: fmt.Sprint(d.Data.Editable) == "1",
				})
			}
		}
		if len(page.Detectors) == 0 {
			break
		}
	}
	return out, nil
}

// Activate activates detectors and waits until FMC reports them active.
// FMC often keeps the activate call open for minutes, so a timeout falls back to polling.
func (c *Client) Activate(uuids []string, names map[string]bool, progress func(string)) (map[string]bool, error) {
	_, err := c.Call("SF::Cache::RNADetector::activateDetectors", []any{uuids}, "", 3*time.Minute)
	if err != nil {
		var fe *Error
		if errors.As(err, &fe) {
			return nil, err
		}
		progress("activation request is still running on FMC; waiting for the detector state")
	}
	want := map[string]bool{}
	for _, u := range uuids {
		want[u] = true
	}
	deadline := time.Now().Add(6 * time.Minute)
	for {
		list, err := c.Detectors(names)
		if err != nil {
			return nil, err
		}
		active := map[string]bool{}
		done := true
		for _, ds := range list {
			for _, d := range ds {
				if want[d.UUID] {
					active[d.UUID] = d.Active
					done = done && d.Active
				}
			}
		}
		if done && len(active) == len(want) {
			return active, nil
		}
		if time.Now().After(deadline) {
			return active, fail("FMC did not report all detectors as active within 6 minutes")
		}
		time.Sleep(c.PollEvery)
	}
}

// ServerVersion is the FMC version shown by the Web UI after Login ("" when not found).
// The REST API is deliberately not used: requesting a REST token for the same
// account logs out the Web UI session that the import relies on.
func (c *Client) ServerVersion() string { return c.version }

func parseVersion(page []byte) string {
	if m := buildRE.FindSubmatch(page); m != nil {
		return fmt.Sprintf("%s (build %s)", m[1], m[2])
	}
	if m := titleVerRE.FindSubmatch(page); m != nil {
		return fmt.Sprintf("%s (build %s)", m[1], m[2])
	}
	return ""
}
