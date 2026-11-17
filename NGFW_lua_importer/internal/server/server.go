// Package server serves the local web UI and its JSON API.
package server

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	"embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io/fs"
	"net"
	"net/http"
	"runtime"
	"strconv"
	"strings"
	"time"

	"ngfw-lua-importer/internal/fmc"
	"ngfw-lua-importer/internal/library"
	"ngfw-lua-importer/internal/version"
)

//go:embed web
var webFS embed.FS

// Server is the local UI. It must only listen on loopback unless the user asks otherwise.
type Server struct {
	lib      *library.Client
	settings *settingsStore
	jobs     *jobRunner
	token    string
	port     string
	quit     chan struct{}
}

// New builds the server; settingsPath "" uses the per-user config directory.
func New(lib *library.Client, settingsPath string) *Server {
	if settingsPath == "" {
		settingsPath = defaultSettingsPath()
	}
	b := make([]byte, 24)
	_, _ = rand.Read(b)
	return &Server{
		lib:      lib,
		settings: &settingsStore{path: settingsPath},
		jobs:     &jobRunner{lib: lib, newClient: realClient},
		token:    hex.EncodeToString(b),
		quit:     make(chan struct{}),
	}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"detail": msg})
}

func decode(w http.ResponseWriter, r *http.Request, v any) error {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	return json.NewDecoder(r.Body).Decode(v)
}

// Handler returns the routes wrapped with the local-only guards.
// port is the listening port, used to validate the Host header.
func (s *Server) Handler(port string) http.Handler {
	s.port = port
	mux := http.NewServeMux()
	static, _ := fs.Sub(webFS, "web")
	mux.Handle("GET /static/", http.StripPrefix("/static/", http.FileServer(http.FS(static))))
	mux.HandleFunc("GET /{$}", s.index)
	mux.HandleFunc("GET /api/info", s.info)
	mux.HandleFunc("GET /api/library", s.library)
	mux.HandleFunc("GET /api/lua", s.lua)
	mux.HandleFunc("POST /api/fmc/test", s.testFMC)
	mux.HandleFunc("POST /api/import", s.startImport)
	mux.HandleFunc("GET /api/job", s.job)
	mux.HandleFunc("POST /api/settings", s.saveSettings)
	mux.HandleFunc("POST /api/quit", s.quitApp)
	return s.guard(mux)
}

// guard blocks DNS-rebinding (Host check) and cross-site requests (per-run token on every API call).
func (s *Server) guard(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		host, port, err := net.SplitHostPort(r.Host)
		if err != nil || port != s.port || !(host == "127.0.0.1" || host == "localhost" || host == "::1") {
			http.Error(w, "forbidden host", http.StatusForbidden)
			return
		}
		if strings.HasPrefix(r.URL.Path, "/api/") {
			got := r.Header.Get("X-Token")
			if subtle.ConstantTimeCompare([]byte(got), []byte(s.token)) != 1 {
				writeErr(w, http.StatusForbidden, "missing or invalid token; reload the page")
				return
			}
		}
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("Referrer-Policy", "no-referrer")
		next.ServeHTTP(w, r)
	})
}

func (s *Server) index(w http.ResponseWriter, _ *http.Request) {
	page, err := webFS.ReadFile("web/index.html")
	if err != nil {
		http.Error(w, "missing UI", http.StatusInternalServerError)
		return
	}
	html := strings.Replace(string(page), "__TOKEN__", s.token, 1)
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Security-Policy",
		"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
	_, _ = w.Write([]byte(html))
}

func (s *Server) info(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{
		"name":       version.Name,
		"version":    version.Version,
		"tested_fmc": version.TestedFMC,
		"contact":    version.Contact,
		"method":     version.Method,
		"os":         runtime.GOOS + "/" + runtime.GOARCH,
		"library":    s.lib.Loc.RepoURL(),
		"settings":   s.settings.load(),
	})
}

func (s *Server) library(w http.ResponseWriter, r *http.Request) {
	snap, err := s.lib.Snapshot(r.URL.Query().Get("refresh") == "1")
	if err != nil {
		writeErr(w, http.StatusBadGateway, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, snap)
}

func (s *Server) lua(w http.ResponseWriter, r *http.Request) {
	ver, err := strconv.Atoi(r.URL.Query().Get("version"))
	if err != nil {
		writeErr(w, http.StatusBadRequest, "invalid version")
		return
	}
	data, _, err := s.lib.ReadLua(r.URL.Query().Get("app_name"), ver)
	if err != nil {
		writeErr(w, http.StatusBadGateway, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{"lua": string(data)})
}

func (s *Server) remember(l FMCLogin) {
	st := s.settings.load()
	st.Host, st.Username, st.VerifyTLS = strings.TrimSpace(l.Host), strings.TrimSpace(l.Username), l.VerifyTLS
	_ = s.settings.save(st)
}

func (s *Server) testFMC(w http.ResponseWriter, r *http.Request) {
	var l FMCLogin
	if err := decode(w, r, &l); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid request")
		return
	}
	if s.jobs.running() {
		// A second login with the same account would log out the running import.
		writeErr(w, http.StatusConflict, "an FMC import is running; test the connection after it finishes")
		return
	}
	c, err := fmc.New(l.Host, l.Username, l.Password, l.VerifyTLS)
	if err != nil {
		writeErr(w, http.StatusBadRequest, err.Error())
		return
	}
	if err := c.Login(); err != nil {
		writeErr(w, http.StatusBadGateway, err.Error())
		return
	}
	s.remember(l)
	writeJSON(w, http.StatusOK, map[string]any{"ok": true, "fmc_version": c.ServerVersion(), "fmc": c.Base})
}

func (s *Server) startImport(w http.ResponseWriter, r *http.Request) {
	var body struct {
		FMC      FMCLogin `json:"fmc"`
		Items    []Item   `json:"items"`
		Activate bool     `json:"activate"`
	}
	if err := decode(w, r, &body); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid request")
		return
	}
	if len(body.Items) == 0 || len(body.Items) > 500 {
		writeErr(w, http.StatusBadRequest, "select 1-500 detectors")
		return
	}
	if _, err := fmc.NormalizeHost(body.FMC.Host); err != nil {
		writeErr(w, http.StatusBadRequest, err.Error())
		return
	}
	if body.FMC.Username == "" || body.FMC.Password == "" {
		writeErr(w, http.StatusBadRequest, "FMC username and password are required")
		return
	}
	job, err := s.jobs.start(body.FMC, body.Items, body.Activate)
	if err != nil {
		writeErr(w, http.StatusConflict, err.Error())
		return
	}
	s.remember(body.FMC)
	writeJSON(w, http.StatusAccepted, job)
}

func (s *Server) job(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"job": s.jobs.snapshot()})
}

func (s *Server) saveSettings(w http.ResponseWriter, r *http.Request) {
	// Every field is optional so the language toggle and the FMC "Save" button can update independently.
	var body struct {
		Lang      *string `json:"lang"`
		Host      *string `json:"host"`
		Username  *string `json:"username"`
		VerifyTLS *bool   `json:"verify_tls"`
	}
	if err := decode(w, r, &body); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid request")
		return
	}
	st := s.settings.load()
	if body.Lang != nil {
		if *body.Lang != "zh" && *body.Lang != "en" {
			writeErr(w, http.StatusBadRequest, "invalid language")
			return
		}
		st.Lang = *body.Lang
	}
	if body.Host != nil {
		host := strings.TrimSpace(*body.Host)
		if host != "" {
			if _, err := fmc.NormalizeHost(host); err != nil {
				writeErr(w, http.StatusBadRequest, err.Error())
				return
			}
		}
		st.Host = host
	}
	if body.Username != nil {
		st.Username = strings.TrimSpace(*body.Username)
	}
	if body.VerifyTLS != nil {
		st.VerifyTLS = *body.VerifyTLS
	}
	if err := s.settings.save(st); err != nil {
		writeErr(w, http.StatusInternalServerError, err.Error())
		return
	}
	writeJSON(w, http.StatusOK, st)
}

// quitApp stops the program; the macOS app has no window or Dock icon, so the UI is the way to quit.
func (s *Server) quitApp(w http.ResponseWriter, _ *http.Request) {
	if s.jobs.running() {
		writeErr(w, http.StatusConflict, "an FMC import is still running")
		return
	}
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
	select {
	case <-s.quit:
	default:
		close(s.quit)
	}
}

// ListenAndServe serves on ln until the process exits or the UI asks to quit.
func (s *Server) ListenAndServe(ln net.Listener) error {
	_, port, _ := net.SplitHostPort(ln.Addr().String())
	srv := &http.Server{Handler: s.Handler(port), ReadHeaderTimeout: 10 * time.Second}
	go func() {
		<-s.quit
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		_ = srv.Shutdown(ctx)
	}()
	err := srv.Serve(ln)
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}
