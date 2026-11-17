// NGFW Lua Importer: browse the shared OpenAppID Lua library and upload selected detectors to Cisco FMC.
package main

import (
	"flag"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
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

// inAppBundle reports whether the program runs as the macOS .app, which has no console to print to.
func inAppBundle() bool {
	exe, err := os.Executable()
	return err == nil && runtime.GOOS == "darwin" && strings.Contains(exe, ".app/Contents/MacOS/")
}

// fail reports a fatal error on stderr and, inside the macOS app, in a dialog.
func fail(code int, msg string) {
	fmt.Fprintln(os.Stderr, msg)
	if inAppBundle() {
		script := "display dialog " + strconv.Quote(msg) + ` with title "NGFW Lua Importer" buttons {"OK"} default button 1 with icon stop`
		_ = exec.Command("osascript", "-e", script).Run()
	}
	os.Exit(code)
}

// alreadyRunning reports whether another NGFW Lua Importer already serves addr.
func alreadyRunning(addr string) bool {
	c := &http.Client{Timeout: 2 * time.Second}
	res, err := c.Get("http://" + addr + "/")
	if err != nil {
		return false
	}
	defer res.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(res.Body, 4096))
	return res.StatusCode == http.StatusOK && strings.Contains(string(body), "<title>"+version.Name+"</title>")
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
		fail(2, "-listen must be a loopback address such as 127.0.0.1:8790")
	}

	loc := library.Location{Owner: *owner, Repo: *repo, Branch: *branch, Dir: *dir, MirrorFallback: *mirror}
	if err := loc.Validate(); err != nil {
		fail(2, err.Error())
	}
	lib := &library.Client{Loc: loc, HTTP: &http.Client{
		Timeout:   30 * time.Second,
		Transport: &http.Transport{Proxy: netproxy.ForInternet()},
	}}

	ln, err := net.Listen("tcp", *listen)
	if err != nil {
		if alreadyRunning(*listen) {
			fmt.Printf("%s is already running; opening http://%s/\n", version.Name, *listen)
			if !*noBrowser {
				openBrowser("http://" + *listen + "/")
			}
			return
		}
		fail(1, fmt.Sprintf("cannot listen on %s: %v", *listen, err))
	}
	url := "http://" + ln.Addr().String() + "/"
	fmt.Printf("%s %s\nOpen %s in your browser (Ctrl+C or the Quit button to stop)\n", version.Name, version.Version, url)
	if !*noBrowser {
		go openBrowser(url)
	}
	if err := server.New(lib, "").ListenAndServe(ln); err != nil {
		fail(1, err.Error())
	}
}
