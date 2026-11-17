//go:build !windows

package netproxy

func hasEnvProxy() bool { return true }

func systemProxy() string { return "" }
