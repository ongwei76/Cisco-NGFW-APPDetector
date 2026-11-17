// NGFW Lua Importer: browse the shared OpenAppID Lua library and upload selected detectors to Cisco FMC.
package main

import (
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"time"

	"ngfw-lua-importer/internal/library"
	"ngfw-lua-importer/internal/netproxy"
	"ngfw-lua-importer/internal/server"
	"ngfw-lua-importer/internal/version"
)

func openBrowser(url string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "windows":
		cmd = exec.Command("rundll32", "url.dll,FileProtocolHandler", url)
	case "darwin":
		cmd = exec.Command("open", url)
	default:
		cmd = exec.Command("xdg-open", url)
	}
	_ = cmd.Start()
}

func main() {
	listen := flag.String("listen", "127.0.0.1:8790", "local address for the web UI (loopback only)")
	noBrowser := flag.Bool("no-browser", false, "do not open the browser automatically")
	showVersion := flag.Bool("version", false, "print version and exit")
	owner := flag.String("owner", "ongwei76", "GitHub owner of the shared library")
	repo := flag.String("repo", "Cisco-NGFW-APPDetector", "GitHub repository of the shared library")
	branch := flag.String("branch", "main", "library branch")
	dir := flag.String("dir", "library", "library directory inside the repository")
	mirror := flag.Bool("mirror", true, "fall back to the jsDelivr mirror when GitHub is unreachable")
	flag.Parse()

	if *showVersion {
		fmt.Printf("%s %s (tested with FMC %s)\n%s\nCompatibility issues: %s\n",
			version.Name, version.Version, version.TestedFMC, version.Method, version.Contact)
		return
	}

	host, _, err := net.SplitHostPort(*listen)
	if err != nil || !(host == "127.0.0.1" || host == "localhost" || host == "::1") {
		fmt.Fprintln(os.Stderr, "-listen must be a loopback address such as 127.0.0.1:8790")
		os.Exit(2)
	}

	loc := library.Location{Owner: *owner, Repo: *repo, Branch: *branch, Dir: *dir, MirrorFallback: *mirror}
	if err := loc.Validate(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(2)
	}
	lib := &library.Client{Loc: loc, HTTP: &http.Client{
		Timeout:   30 * time.Second,
		Transport: &http.Transport{Proxy: netproxy.ForInternet()},
	}}

	ln, err := net.Listen("tcp", *listen)
	if err != nil {
		fmt.Fprintf(os.Stderr, "cannot listen on %s: %v\n", *listen, err)
		os.Exit(1)
	}
	url := "http://" + ln.Addr().String() + "/"
	fmt.Printf("%s %s\nOpen %s in your browser (Ctrl+C to quit)\n", version.Name, version.Version, url)
	if !*noBrowser {
		go openBrowser(url)
	}
	if err := server.New(lib, "").ListenAndServe(ln); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
