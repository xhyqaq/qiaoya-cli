package installers

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"time"

	"github.com/xhyqaq/qiaoya-cli/internal/qiaoya/assets"
	"github.com/xhyqaq/qiaoya-cli/internal/qiaoya/metadata"
)

const (
	AgentCodex    = "codex"
	AgentClaude   = "claude"
	AgentCursor   = "cursor"
	AgentWindsurf = "windsurf"
	AgentOpenClaw = "openclaw"

	windsurfBlockStart = "<!-- qiaoya:start -->"
	windsurfBlockEnd   = "<!-- qiaoya:end -->"
)

type Options struct {
	Agents     []string
	HomeDir    string
	WorkDir    string
	ProjectDir string
	CodexHome  string
	ClaudeHome string
	BinDir     string
	DryRun     bool
	Writer     io.Writer
}

type Result struct {
	Agent   string `json:"agent"`
	Path    string `json:"path"`
	Status  string `json:"status"`
	Message string `json:"message,omitempty"`
}

type DoctorReport struct {
	Version     string   `json:"version"`
	BinaryPath  string   `json:"binaryPath"`
	BinaryOK    bool     `json:"binaryOk"`
	AgentChecks []Result `json:"agentChecks"`
}

func Install(options Options) ([]Result, error) {
	options = normalizeOptions(options)
	runtimePath, err := installRuntimeBinary(options)
	if err != nil {
		return nil, err
	}

	agents := expandAgents(options.Agents)
	results := make([]Result, 0, len(agents))
	for _, agent := range agents {
		result := installAgent(agent, runtimePath, options)
		results = append(results, result)
	}
	return results, nil
}

func Uninstall(options Options) ([]Result, error) {
	options = normalizeOptions(options)
	agents := expandAgents(options.Agents)
	results := make([]Result, 0, len(agents))
	for _, agent := range agents {
		results = append(results, uninstallAgent(agent, options))
	}
	return results, nil
}

func Doctor(options Options) DoctorReport {
	options = normalizeOptions(options)
	binaryPath := runtimeTargetPath(options)
	report := DoctorReport{
		Version:    metadata.Version,
		BinaryPath: binaryPath,
		BinaryOK:   executableExists(binaryPath),
	}
	for _, agent := range expandAgents(options.Agents) {
		report.AgentChecks = append(report.AgentChecks, checkAgent(agent, options))
	}
	return report
}

func normalizeOptions(options Options) Options {
	home := options.HomeDir
	if home == "" {
		home, _ = os.UserHomeDir()
	}
	options.HomeDir = home
	if options.WorkDir == "" {
		options.WorkDir, _ = os.Getwd()
	}
	if options.ProjectDir == "" {
		options.ProjectDir = options.WorkDir
	}
	if options.CodexHome == "" {
		options.CodexHome = filepath.Join(home, ".codex")
	}
	if options.ClaudeHome == "" {
		options.ClaudeHome = filepath.Join(home, ".claude")
	}
	if options.BinDir == "" {
		options.BinDir = filepath.Join(home, ".qiaoya", "bin")
	}
	if len(options.Agents) == 0 {
		options.Agents = []string{"auto"}
	}
	if options.Writer == nil {
		options.Writer = io.Discard
	}
	return options
}

func expandAgents(values []string) []string {
	seen := map[string]bool{}
	add := func(agent string, out *[]string) {
		agent = strings.ToLower(strings.TrimSpace(agent))
		if agent == "" || seen[agent] {
			return
		}
		seen[agent] = true
		*out = append(*out, agent)
	}

	var out []string
	for _, raw := range values {
		for _, token := range strings.Split(raw, ",") {
			token = strings.ToLower(strings.TrimSpace(token))
			switch token {
			case "", "auto":
				add(AgentCodex, &out)
				add(AgentClaude, &out)
				add(AgentOpenClaw, &out)
				add(AgentCursor, &out)
				add(AgentWindsurf, &out)
			case "all":
				add(AgentCodex, &out)
				add(AgentClaude, &out)
				add(AgentOpenClaw, &out)
				add(AgentCursor, &out)
				add(AgentWindsurf, &out)
			default:
				add(token, &out)
			}
		}
	}
	return out
}

func installRuntimeBinary(options Options) (string, error) {
	target := runtimeTargetPath(options)
	if options.DryRun {
		return target, nil
	}

	source, err := os.Executable()
	if err != nil {
		return "", err
	}
	source, _ = filepath.EvalSymlinks(source)
	targetEval, _ := filepath.EvalSymlinks(target)
	if targetEval != "" && source == targetEval {
		return target, nil
	}

	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return "", err
	}
	temp := fmt.Sprintf("%s.tmp-%d", target, os.Getpid())
	if err := copyFile(source, temp, 0o755); err != nil {
		return "", err
	}
	if err := os.Rename(temp, target); err != nil {
		_ = os.Remove(temp)
		return "", err
	}
	return target, nil
}

func runtimeTargetPath(options Options) string {
	name := metadata.AppName
	if runtime.GOOS == "windows" {
		name += ".exe"
	}
	return filepath.Join(options.BinDir, name)
}

func installAgent(agent, runtimePath string, options Options) Result {
	switch agent {
	case AgentCodex:
		return installSkillDir(agent, filepath.Join(options.CodexHome, "skills", "qiaoya"), runtimePath, options)
	case AgentClaude:
		return installSkillDir(agent, filepath.Join(options.ClaudeHome, "skills", "qiaoya"), runtimePath, options)
	case AgentOpenClaw:
		return installSkillDir(agent, filepath.Join(options.HomeDir, ".openclaw", "skills", "qiaoya"), runtimePath, options)
	case AgentCursor:
		return installProjectRule(agent, options.ProjectDir, filepath.Join(".cursor", "rules", "qiaoya.mdc"), "rules/cursor.mdc", options)
	case AgentWindsurf:
		return installWindsurf(options)
	default:
		return Result{Agent: agent, Status: "skipped", Message: "不支持的 agent"}
	}
}

func uninstallAgent(agent string, options Options) Result {
	var target string
	switch agent {
	case AgentCodex:
		target = filepath.Join(options.CodexHome, "skills", "qiaoya")
	case AgentClaude:
		target = filepath.Join(options.ClaudeHome, "skills", "qiaoya")
	case AgentOpenClaw:
		target = filepath.Join(options.HomeDir, ".openclaw", "skills", "qiaoya")
	case AgentCursor:
		target = filepath.Join(options.ProjectDir, ".cursor", "rules", "qiaoya.mdc")
	case AgentWindsurf:
		globalTarget := filepath.Join(options.HomeDir, ".codeium", "windsurf", "memories", "global_rules.md")
		projectTarget := filepath.Join(options.ProjectDir, ".windsurf", "rules", "qiaoya.md")
		if options.DryRun {
			return Result{Agent: agent, Path: globalTarget + " + " + projectTarget, Status: "dry-run"}
		}
		if err := removeMarkedBlock(globalTarget, windsurfBlockStart, windsurfBlockEnd); err != nil {
			return Result{Agent: agent, Path: globalTarget, Status: "failed", Message: err.Error()}
		}
		if looksLikeProject(options.ProjectDir) {
			if err := os.RemoveAll(projectTarget); err != nil {
				return Result{Agent: agent, Path: projectTarget, Status: "failed", Message: err.Error()}
			}
		}
		return Result{Agent: agent, Path: globalTarget, Status: "removed"}
	default:
		return Result{Agent: agent, Status: "skipped", Message: "不支持的 agent"}
	}
	if options.DryRun {
		return Result{Agent: agent, Path: target, Status: "dry-run"}
	}
	if err := os.RemoveAll(target); err != nil {
		return Result{Agent: agent, Path: target, Status: "failed", Message: err.Error()}
	}
	return Result{Agent: agent, Path: target, Status: "removed"}
}

func checkAgent(agent string, options Options) Result {
	var target string
	switch agent {
	case AgentCodex:
		target = filepath.Join(options.CodexHome, "skills", "qiaoya", "SKILL.md")
	case AgentClaude:
		target = filepath.Join(options.ClaudeHome, "skills", "qiaoya", "SKILL.md")
	case AgentOpenClaw:
		target = filepath.Join(options.HomeDir, ".openclaw", "skills", "qiaoya", "SKILL.md")
	case AgentCursor:
		target = filepath.Join(options.ProjectDir, ".cursor", "rules", "qiaoya.mdc")
	case AgentWindsurf:
		globalTarget := filepath.Join(options.HomeDir, ".codeium", "windsurf", "memories", "global_rules.md")
		projectTarget := filepath.Join(options.ProjectDir, ".windsurf", "rules", "qiaoya.md")
		if fileContains(globalTarget, windsurfBlockStart) || fileExists(projectTarget) {
			return Result{Agent: agent, Path: globalTarget, Status: "ok"}
		}
		return Result{Agent: agent, Path: globalTarget, Status: "missing"}
	default:
		return Result{Agent: agent, Status: "skipped", Message: "不支持的 agent"}
	}
	if fileExists(target) {
		return Result{Agent: agent, Path: target, Status: "ok"}
	}
	return Result{Agent: agent, Path: target, Status: "missing"}
}

func installSkillDir(agent, target, runtimePath string, options Options) Result {
	if options.DryRun {
		return Result{Agent: agent, Path: target, Status: "dry-run"}
	}

	parent := filepath.Dir(target)
	if err := os.MkdirAll(parent, 0o755); err != nil {
		return Result{Agent: agent, Path: target, Status: "failed", Message: err.Error()}
	}
	temp, err := os.MkdirTemp(parent, ".qiaoya-skill-*")
	if err != nil {
		return Result{Agent: agent, Path: target, Status: "failed", Message: err.Error()}
	}
	defer os.RemoveAll(temp)

	if err := writeSkillBundle(temp, runtimePath, agent); err != nil {
		return Result{Agent: agent, Path: target, Status: "failed", Message: err.Error()}
	}
	if err := swapDir(temp, target); err != nil {
		return Result{Agent: agent, Path: target, Status: "failed", Message: err.Error()}
	}
	return Result{Agent: agent, Path: target, Status: "installed"}
}

func installProjectRule(agent, projectDir, relativeTarget, assetPath string, options Options) Result {
	if strings.TrimSpace(projectDir) == "" || !looksLikeProject(projectDir) {
		return Result{Agent: agent, Path: projectDir, Status: "skipped", Message: "未检测到项目目录；可在项目根目录执行或传 --project-dir"}
	}

	target := filepath.Join(projectDir, relativeTarget)
	if options.DryRun {
		return Result{Agent: agent, Path: target, Status: "dry-run"}
	}
	content, err := assets.FS.ReadFile(assetPath)
	if err != nil {
		return Result{Agent: agent, Path: target, Status: "failed", Message: err.Error()}
	}
	if err := writeFileAtomic(target, content, 0o644); err != nil {
		return Result{Agent: agent, Path: target, Status: "failed", Message: err.Error()}
	}
	return Result{Agent: agent, Path: target, Status: "installed"}
}

func installWindsurf(options Options) Result {
	globalTarget := filepath.Join(options.HomeDir, ".codeium", "windsurf", "memories", "global_rules.md")
	projectTarget := filepath.Join(options.ProjectDir, ".windsurf", "rules", "qiaoya.md")
	if options.DryRun {
		path := globalTarget
		if looksLikeProject(options.ProjectDir) {
			path += " + " + projectTarget
		}
		return Result{Agent: AgentWindsurf, Path: path, Status: "dry-run"}
	}

	globalContent, err := assets.FS.ReadFile("rules/windsurf-global.md")
	if err != nil {
		return Result{Agent: AgentWindsurf, Path: globalTarget, Status: "failed", Message: err.Error()}
	}
	block := windsurfBlockStart + "\n" + string(globalContent) + "\n" + windsurfBlockEnd + "\n"
	if err := upsertMarkedBlock(globalTarget, windsurfBlockStart, windsurfBlockEnd, block); err != nil {
		return Result{Agent: AgentWindsurf, Path: globalTarget, Status: "failed", Message: err.Error()}
	}

	if looksLikeProject(options.ProjectDir) {
		result := installProjectRule(AgentWindsurf, options.ProjectDir, filepath.Join(".windsurf", "rules", "qiaoya.md"), "rules/windsurf.md", options)
		if result.Status == "failed" {
			return result
		}
		return Result{Agent: AgentWindsurf, Path: globalTarget + " + " + projectTarget, Status: "installed"}
	}
	return Result{Agent: AgentWindsurf, Path: globalTarget, Status: "installed"}
}

func writeSkillBundle(target, runtimePath, agent string) error {
	if err := fs.WalkDir(assets.FS, "skills/qiaoya", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel("skills/qiaoya", path)
		if err != nil || rel == "." {
			return err
		}
		outPath := filepath.Join(target, filepath.FromSlash(rel))
		if d.IsDir() {
			return os.MkdirAll(outPath, 0o755)
		}
		content, err := assets.FS.ReadFile(path)
		if err != nil {
			return err
		}
		return writeFileAtomic(outPath, content, 0o644)
	}); err != nil {
		return err
	}

	if err := os.MkdirAll(filepath.Join(target, "scripts"), 0o755); err != nil {
		return err
	}
	if err := writeRuntimeShims(target, runtimePath); err != nil {
		return err
	}
	if err := writeFileAtomic(filepath.Join(target, "VERSION"), []byte(metadata.Version+"\n"), 0o644); err != nil {
		return err
	}
	return writeInstallMeta(target, runtimePath, agent)
}

func writeRuntimeShims(target, runtimePath string) error {
	unixShim := fmt.Sprintf("#!/usr/bin/env sh\nexec %q \"$@\"\n", runtimePath)
	if err := writeFileAtomic(filepath.Join(target, "scripts", "qiaoya"), []byte(unixShim), 0o755); err != nil {
		return err
	}
	cmdShim := fmt.Sprintf("@echo off\r\n%q %%*\r\n", runtimePath)
	return writeFileAtomic(filepath.Join(target, "scripts", "qiaoya.cmd"), []byte(cmdShim), 0o755)
}

func writeInstallMeta(target, runtimePath, agent string) error {
	payload := map[string]any{
		"version":     metadata.Version,
		"commit":      metadata.Commit,
		"date":        metadata.Date,
		"agent":       agent,
		"runtimePath": runtimePath,
		"installedAt": time.Now().UTC().Format(time.RFC3339),
	}
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	raw = append(raw, '\n')
	return writeFileAtomic(filepath.Join(target, "install-meta.json"), raw, 0o644)
}

func swapDir(temp, target string) error {
	backup := fmt.Sprintf("%s.backup-%d", target, time.Now().UnixNano())
	hadOld := false
	if _, err := os.Stat(target); err == nil {
		hadOld = true
		if err := os.Rename(target, backup); err != nil {
			return err
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return err
	}

	if err := os.Rename(temp, target); err != nil {
		if hadOld {
			_ = os.Rename(backup, target)
		}
		return err
	}
	if hadOld {
		_ = os.RemoveAll(backup)
	}
	return nil
}

func looksLikeProject(path string) bool {
	if path == "" {
		return false
	}
	markers := []string{".git", ".cursor", ".windsurf", "package.json", "go.mod", "pom.xml", "pyproject.toml"}
	for _, marker := range markers {
		if _, err := os.Stat(filepath.Join(path, marker)); err == nil {
			return true
		}
	}
	return false
}

func writeFileAtomic(path string, data []byte, mode fs.FileMode) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	temp := fmt.Sprintf("%s.tmp-%d", path, os.Getpid())
	if err := os.WriteFile(temp, data, mode); err != nil {
		return err
	}
	if err := os.Chmod(temp, mode); err != nil {
		_ = os.Remove(temp)
		return err
	}
	if err := os.Rename(temp, path); err != nil {
		_ = os.Remove(temp)
		return err
	}
	return nil
}

func copyFile(source, target string, mode fs.FileMode) error {
	in, err := os.Open(source)
	if err != nil {
		return err
	}
	defer in.Close()

	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		return err
	}
	out, err := os.OpenFile(target, os.O_CREATE|os.O_WRONLY|os.O_TRUNC, mode)
	if err != nil {
		return err
	}
	if _, err := io.Copy(out, in); err != nil {
		_ = out.Close()
		return err
	}
	if err := out.Close(); err != nil {
		return err
	}
	return os.Chmod(target, mode)
}

func fileExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir()
}

func fileContains(path, needle string) bool {
	raw, err := os.ReadFile(path)
	return err == nil && strings.Contains(string(raw), needle)
}

func executableExists(path string) bool {
	info, err := os.Stat(path)
	return err == nil && !info.IsDir() && info.Size() > 0
}

func Sha256File(path string) (string, error) {
	file, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer file.Close()

	hash := sha256.New()
	if _, err := io.Copy(hash, file); err != nil {
		return "", err
	}
	return hex.EncodeToString(hash.Sum(nil)), nil
}

func upsertMarkedBlock(path, start, end, block string) error {
	existing := ""
	if raw, err := os.ReadFile(path); err == nil {
		existing = string(raw)
	} else if !errors.Is(err, os.ErrNotExist) {
		return err
	}

	next := replaceMarkedBlock(existing, start, end, block)
	return writeFileAtomic(path, []byte(next), 0o644)
}

func removeMarkedBlock(path, start, end string) error {
	raw, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return err
	}
	next := replaceMarkedBlock(string(raw), start, end, "")
	if strings.TrimSpace(next) == "" {
		return os.Remove(path)
	}
	return writeFileAtomic(path, []byte(next), 0o644)
}

func replaceMarkedBlock(existing, start, end, block string) string {
	startIndex := strings.Index(existing, start)
	endIndex := strings.Index(existing, end)
	if startIndex >= 0 && endIndex >= startIndex {
		endIndex += len(end)
		for endIndex < len(existing) && (existing[endIndex] == '\n' || existing[endIndex] == '\r') {
			endIndex++
		}
		prefix := strings.TrimRight(existing[:startIndex], "\r\n")
		suffix := strings.TrimLeft(existing[endIndex:], "\r\n")
		if strings.TrimSpace(block) == "" {
			if prefix == "" {
				return suffix
			}
			if suffix == "" {
				return prefix + "\n"
			}
			return prefix + "\n\n" + suffix
		}
		if prefix == "" {
			return strings.TrimRight(block, "\r\n") + "\n" + suffix
		}
		return prefix + "\n\n" + strings.TrimRight(block, "\r\n") + "\n" + suffix
	}
	if strings.TrimSpace(block) == "" {
		return existing
	}
	if strings.TrimSpace(existing) == "" {
		return strings.TrimRight(block, "\r\n") + "\n"
	}
	return strings.TrimRight(existing, "\r\n") + "\n\n" + strings.TrimRight(block, "\r\n") + "\n"
}

func SupportedAgents() []string {
	agents := []string{AgentCodex, AgentClaude, AgentCursor, AgentWindsurf, AgentOpenClaw}
	sort.Strings(agents)
	return agents
}
