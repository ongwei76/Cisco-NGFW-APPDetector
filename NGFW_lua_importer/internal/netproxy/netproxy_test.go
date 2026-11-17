package netproxy

import "testing"

func TestParseServer(t *testing.T) {
	cases := map[string]string{
		"proxy.corp:8080":    "http://proxy.corp:8080",
		"http://p:3128":      "http://p:3128",
		"http=a:1;https=b:2": "http://b:2",
		"ftp=f:21;http=a:1":  "http://a:1",
		"socks=s:1080":       "",
		"":                   "",
	}
	for in, want := range cases {
		got := ""
		if u := parseServer(in); u != nil {
			got = u.String()
		}
		if got != want {
			t.Errorf("parseServer(%q) = %q, want %q", in, got, want)
		}
	}
}
