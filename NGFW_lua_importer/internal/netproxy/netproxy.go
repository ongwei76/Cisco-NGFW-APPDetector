// Package netproxy picks the HTTP proxy used to reach GitHub / jsDelivr.
//
// Go only reads proxy environment variables. Corporate Windows machines often
// configure the proxy in Internet Options instead, so on Windows the registry
// proxy is used when no HTTP(S)_PROXY variable is set.
package netproxy

import (
	"net/http"
	"net/url"
	"strings"
)

// ForInternet returns the proxy function for public-internet requests.
func ForInternet() func(*http.Request) (*url.URL, error) {
	if hasEnvProxy() {
		return http.ProxyFromEnvironment
	}
	if server := systemProxy(); server != "" {
		if u := parseServer(server); u != nil {
			return http.ProxyURL(u)
		}
	}
	return http.ProxyFromEnvironment
}

// parseServer understands "host:port", "http://host:port" and the
// per-scheme form "http=host:port;https=host:port" (https preferred).
func parseServer(value string) *url.URL {
	value = strings.TrimSpace(value)
	if strings.Contains(value, "=") {
		chosen := ""
		for _, part := range strings.Split(value, ";") {
			kv := strings.SplitN(strings.TrimSpace(part), "=", 2)
			if len(kv) != 2 {
				continue
			}
			switch strings.ToLower(kv[0]) {
			case "https":
				chosen = kv[1]
			case "http":
				if chosen == "" {
					chosen = kv[1]
				}
			}
		}
		value = chosen
	}
	if value == "" {
		return nil
	}
	if !strings.Contains(value, "://") {
		value = "http://" + value
	}
	u, err := url.Parse(value)
	if err != nil || u.Host == "" {
		return nil
	}
	return u
}
