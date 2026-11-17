package server

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sync"
)

// Settings are remembered between runs. The FMC password is never written to disk.
type Settings struct {
	Host      string `json:"host"`
	Username  string `json:"username"`
	VerifyTLS bool   `json:"verify_tls"`
	Lang      string `json:"lang"`
}

type settingsStore struct {
	path string
	mu   sync.Mutex
}

func defaultSettingsPath() string {
	dir, err := os.UserConfigDir()
	if err != nil {
		dir = "."
	}
	return filepath.Join(dir, "NGFW_Lua_Importer", "settings.json")
}

func (s *settingsStore) load() Settings {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := Settings{Username: "admin", Lang: "zh"}
	if data, err := os.ReadFile(s.path); err == nil {
		_ = json.Unmarshal(data, &out)
	}
	return out
}

func (s *settingsStore) save(v Settings) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := os.MkdirAll(filepath.Dir(s.path), 0o700); err != nil {
		return err
	}
	data, _ := json.MarshalIndent(v, "", "  ")
	tmp := s.path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, s.path)
}
