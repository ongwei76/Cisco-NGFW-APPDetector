package server

import (
	"fmt"
	"strings"
	"sync"
	"time"

	"ngfw-lua-importer/internal/fmc"
	"ngfw-lua-importer/internal/library"
)

// FMCLogin is what the user typed in the connection form.
type FMCLogin struct {
	Host      string `json:"host"`
	Username  string `json:"username"`
	Password  string `json:"password"`
	VerifyTLS bool   `json:"verify_tls"`
}

// Item selects one library entry.
type Item struct {
	AppName string `json:"app_name"`
	Version int    `json:"version"`
}

// ItemResult is the per-detector progress shown in the UI.
type ItemResult struct {
	AppName  string `json:"app_name"`
	Version  int    `json:"version"`
	Status   string `json:"status"` // pending | importing | imported | skipped | error
	Message  string `json:"message"`
	UUID     string `json:"uuid,omitempty"`
	Category string `json:"category,omitempty"`
	Active   *bool  `json:"active,omitempty"`
}

// Job is one import run.
type Job struct {
	ID         string       `json:"id"`
	State      string       `json:"state"` // running | done | failed
	Activate   bool         `json:"activate"`
	FMCHost    string       `json:"fmc_host"`
	FMCVersion string       `json:"fmc_version"`
	Results    []ItemResult `json:"results"`
	Log        []string     `json:"log"`
	Error      string       `json:"error,omitempty"`
	Started    time.Time    `json:"started"`
	Finished   *time.Time   `json:"finished,omitempty"`
}

type jobRunner struct {
	mu  sync.Mutex
	job *Job
	lib *library.Client
	// newClient is replaceable in tests.
	newClient func(FMCLogin) (fmcAPI, error)
}

type fmcAPI interface {
	Login() error
	ServerVersion() string
	Import(fmc.Spec) (fmc.Result, error)
	Detectors(map[string]bool) (map[string][]fmc.Detector, error)
	Activate([]string, map[string]bool, func(string)) (map[string]bool, error)
}

func realClient(l FMCLogin) (fmcAPI, error) {
	return fmc.New(l.Host, l.Username, l.Password, l.VerifyTLS)
}

func (r *jobRunner) running() bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.job != nil && r.job.State == "running"
}

func (r *jobRunner) snapshot() *Job {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.job == nil {
		return nil
	}
	cp := *r.job
	cp.Results = append([]ItemResult(nil), r.job.Results...)
	cp.Log = append([]string(nil), r.job.Log...)
	return &cp
}

func (r *jobRunner) update(fn func(*Job)) {
	r.mu.Lock()
	defer r.mu.Unlock()
	fn(r.job)
}

func (r *jobRunner) logf(format string, a ...any) {
	line := time.Now().Format("15:04:05") + "  " + fmt.Sprintf(format, a...)
	r.update(func(j *Job) { j.Log = append(j.Log, line) })
}

// start launches a job unless one is already running.
func (r *jobRunner) start(login FMCLogin, items []Item, activate bool) (*Job, error) {
	r.mu.Lock()
	if r.job != nil && r.job.State == "running" {
		r.mu.Unlock()
		return nil, fmt.Errorf("an FMC import is already running")
	}
	job := &Job{
		ID: fmt.Sprintf("%d", time.Now().UnixNano()), State: "running", Activate: activate,
		FMCHost: login.Host, Started: time.Now(),
	}
	seen := map[string]bool{}
	for _, it := range items {
		res := ItemResult{AppName: it.AppName, Version: it.Version, Status: "pending"}
		key := strings.ToLower(it.AppName)
		if seen[key] {
			res.Status, res.Message = "skipped", "another version of this application is already selected"
		}
		seen[key] = true
		job.Results = append(job.Results, res)
	}
	r.job = job
	r.mu.Unlock()
	go r.run(login, activate)
	return r.snapshot(), nil
}

func (r *jobRunner) finish(err error) {
	now := time.Now()
	r.update(func(j *Job) {
		j.Finished = &now
		j.State = "done"
		if err != nil {
			j.State, j.Error = "failed", err.Error()
		}
	})
	if err != nil {
		r.logf("stopped: %v", err)
	} else {
		r.logf("finished")
	}
}

func (r *jobRunner) setResult(i int, fn func(*ItemResult)) {
	r.update(func(j *Job) { fn(&j.Results[i]) })
}

func (r *jobRunner) run(login FMCLogin, activate bool) {
	client, err := r.newClient(login)
	if err != nil {
		r.finish(err)
		return
	}
	r.logf("logging in to FMC %s as %s", login.Host, login.Username)
	if err := client.Login(); err != nil {
		r.finish(err)
		return
	}
	ver := client.ServerVersion()
	r.update(func(j *Job) { j.FMCVersion = ver })
	if ver != "" {
		r.logf("FMC version %s", ver)
	} else {
		r.logf("FMC version could not be read (REST API unavailable); continuing")
	}

	job := r.snapshot()
	var toActivate []string
	activateIdx := map[string]int{}
	existingNames := map[string]int{}
	for i, res := range job.Results {
		if res.Status != "pending" {
			continue
		}
		r.setResult(i, func(x *ItemResult) { x.Status = "importing" })
		r.logf("%s v%d: downloading from the shared library", res.AppName, res.Version)
		lua, entry, err := r.lib.ReadLua(res.AppName, res.Version)
		if err != nil {
			r.setResult(i, func(x *ItemResult) { x.Status, x.Message = "error", err.Error() })
			r.logf("%s: %v", res.AppName, err)
			continue
		}
		cat := entry.Category
		if cat == "" {
			cat = "others"
		}
		risk, rel := entry.Risk, entry.BusinessRelevance
		if risk == 0 {
			risk = 2
		}
		if rel == 0 {
			rel = 3
		}
		r.logf("%s: SHA256 verified (category %s), sending to FMC", res.AppName, cat)
		out, err := client.Import(fmc.Spec{
			AppName: entry.AppName, Lua: lua, Category: cat, Risk: risk, BusinessRelevance: rel,
			Description: clip(fmt.Sprintf("NGFW shared Lua library v%d (%s)", entry.Version, entry.Nickname), 200),
		})
		if err != nil {
			r.setResult(i, func(x *ItemResult) { x.Status, x.Message = "error", err.Error() })
			r.logf("%s: %v", res.AppName, err)
			continue
		}
		r.setResult(i, func(x *ItemResult) {
			x.Status, x.Message, x.UUID, x.Category = out.Status, out.Message, out.UUID, out.Category
		})
		r.logf("%s: %s", res.AppName, out.Message)
		if out.Status == "imported" {
			toActivate = append(toActivate, out.UUID)
			activateIdx[out.UUID] = i
		} else if out.Status == "skipped" {
			existingNames[strings.ToLower(res.AppName)] = i
		}
	}

	if activate {
		names := map[string]bool{}
		for _, i := range activateIdx {
			names[strings.ToLower(r.snapshot().Results[i].AppName)] = true
		}
		if len(existingNames) > 0 {
			for n := range existingNames {
				names[n] = true
			}
			list, err := client.Detectors(names)
			if err != nil {
				r.finish(err)
				return
			}
			for n, i := range existingNames {
				for _, d := range list[n] {
					// Only custom (editable) detectors; never touch Cisco built-ins.
					if !d.Editable {
						continue
					}
					if d.Active {
						t := true
						r.setResult(i, func(x *ItemResult) {
							x.UUID, x.Active, x.Message = d.UUID, &t, "already exists in FMC; custom detector is already active"
						})
						continue
					}
					toActivate = append(toActivate, d.UUID)
					activateIdx[d.UUID] = i
					r.setResult(i, func(x *ItemResult) {
						x.UUID, x.Message = d.UUID, "already exists in FMC; activating the existing custom detector"
					})
				}
			}
		}
		if len(toActivate) > 0 {
			r.logf("activating %d detector(s); this can take a few minutes", len(toActivate))
			state, err := client.Activate(toActivate, names, func(s string) { r.logf("%s", s) })
			for uuid, i := range activateIdx {
				on := state[uuid]
				r.setResult(i, func(x *ItemResult) {
					x.Active = &on
					if on {
						x.Message = strings.Replace(x.Message, "(Inactive)", "(Active)", 1)
						if !strings.Contains(x.Message, "(Active)") {
							x.Message = strings.Replace(x.Message, "activating the existing", "activated the existing", 1)
						}
					}
				})
			}
			if err != nil {
				r.finish(err)
				return
			}
			r.logf("activation finished; FMC pushes active detectors to managed devices without a deploy")
		}
	}
	r.finish(nil)
}

func clip(s string, n int) string {
	if len(s) > n {
		return s[:n]
	}
	return s
}
