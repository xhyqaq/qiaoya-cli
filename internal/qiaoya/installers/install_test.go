package installers

import (
	"os"
	"path/filepath"
	"testing"
)

func TestInstallWritesSkillDirsAndProjectRules(t *testing.T) {
	home := t.TempDir()
	project := t.TempDir()
	if err := os.WriteFile(filepath.Join(project, "go.mod"), []byte("module example\n"), 0o644); err != nil {
		t.Fatal(err)
	}

	results, err := Install(Options{
		Agents:     []string{"codex,claude,cursor,windsurf,openclaw"},
		HomeDir:    home,
		ProjectDir: project,
		BinDir:     filepath.Join(home, ".qiaoya", "bin"),
	})
	if err != nil {
		t.Fatalf("Install() error = %v", err)
	}
	if len(results) != 5 {
		t.Fatalf("results len = %d", len(results))
	}

	assertFile(t, filepath.Join(home, ".codex", "skills", "qiaoya", "SKILL.md"))
	assertFile(t, filepath.Join(home, ".claude", "skills", "qiaoya", "SKILL.md"))
	assertFile(t, filepath.Join(home, ".openclaw", "skills", "qiaoya", "SKILL.md"))
	assertFile(t, filepath.Join(project, ".cursor", "rules", "qiaoya.mdc"))
	assertFile(t, filepath.Join(project, ".windsurf", "rules", "qiaoya.md"))
	assertFile(t, filepath.Join(home, ".codeium", "windsurf", "memories", "global_rules.md"))
	assertFile(t, filepath.Join(home, ".qiaoya", "bin", "qiaoya"))
}

func TestProjectRuleSkipsOutsideProject(t *testing.T) {
	home := t.TempDir()
	results, err := Install(Options{
		Agents:     []string{"cursor"},
		HomeDir:    home,
		ProjectDir: t.TempDir(),
		BinDir:     filepath.Join(home, ".qiaoya", "bin"),
	})
	if err != nil {
		t.Fatalf("Install() error = %v", err)
	}
	if results[0].Status != "skipped" {
		t.Fatalf("cursor status = %s", results[0].Status)
	}
}

func TestWindsurfInstallsGlobalRuleOutsideProject(t *testing.T) {
	home := t.TempDir()
	results, err := Install(Options{
		Agents:     []string{"windsurf"},
		HomeDir:    home,
		ProjectDir: t.TempDir(),
		BinDir:     filepath.Join(home, ".qiaoya", "bin"),
	})
	if err != nil {
		t.Fatalf("Install() error = %v", err)
	}
	if results[0].Status != "installed" {
		t.Fatalf("windsurf status = %s", results[0].Status)
	}
	assertFile(t, filepath.Join(home, ".codeium", "windsurf", "memories", "global_rules.md"))
}

func assertFile(t *testing.T, path string) {
	t.Helper()
	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("expected file %s: %v", path, err)
	}
	if info.IsDir() {
		t.Fatalf("expected file, got directory: %s", path)
	}
}
