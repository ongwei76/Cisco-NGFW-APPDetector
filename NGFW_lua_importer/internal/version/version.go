// Package version holds the program identity shown in the UI, the CLI and compatibility reports.
package version

const (
	Name    = "NGFW Lua Importer"
	Version = "1.0.1"
	// TestedFMC lists the FMC releases the upload sequence was verified on.
	TestedFMC = "10.0.1"
	// Contact receives compatibility reports.
	Contact = "yongwli@cisco.com"
	// Method describes how detectors reach FMC (shown in the UI and README).
	Method = "FMC Web UI session (login.cgi + pjb.cgi RNADetector calls + detectors.cgi Lua upload)"
)
