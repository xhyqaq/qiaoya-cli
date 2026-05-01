package cli

import (
	"bytes"
	"strings"
	"testing"
	"time"

	"github.com/xhyqaq/qiaoya-cli/internal/qiaoya/auth"
)

func TestHelpMentionsPublicCommands(t *testing.T) {
	var out bytes.Buffer
	code := New(&out, &bytes.Buffer{}).Run([]string{"--help"})
	if code != 0 {
		t.Fatalf("Run help code = %d", code)
	}
	text := out.String()
	for _, want := range []string{"install", "auth login", "public overview", "ai-news today"} {
		if !strings.Contains(text, want) {
			t.Fatalf("help missing %q:\n%s", want, text)
		}
	}
}

func TestUpdatePrintsInstallCommand(t *testing.T) {
	var out bytes.Buffer
	code := New(&out, &bytes.Buffer{}).Run([]string{"update"})
	if code != 0 {
		t.Fatalf("Run update code = %d", code)
	}
	if !strings.Contains(out.String(), "curl -fsSL") {
		t.Fatalf("update output missing command: %s", out.String())
	}
}

func TestAuthStatusReadsStoredToken(t *testing.T) {
	authFile := t.TempDir() + "/auth.json"
	err := auth.SaveToken(authFile, auth.Token{
		AccessToken: "access-token",
		TokenType:   "Bearer",
		ExpiresIn:   3600,
		Scope:       "openid profile email read",
		BaseURL:     "http://127.0.0.1:8520",
		ClientID:    auth.DefaultClientID,
		ObtainedAt:  time.Now(),
	})
	if err != nil {
		t.Fatal(err)
	}

	var out bytes.Buffer
	code := New(&out, &bytes.Buffer{}).Run([]string{"auth", "status", "--auth-file", authFile})
	if code != 0 {
		t.Fatalf("auth status code = %d, output:\n%s", code, out.String())
	}
	if !strings.Contains(out.String(), auth.DefaultClientID) {
		t.Fatalf("auth status missing client id: %s", out.String())
	}
}

func TestAuthLogoutRemovesStoredToken(t *testing.T) {
	authFile := t.TempDir() + "/auth.json"
	if err := auth.SaveToken(authFile, auth.Token{AccessToken: "access-token"}); err != nil {
		t.Fatal(err)
	}

	var out bytes.Buffer
	code := New(&out, &bytes.Buffer{}).Run([]string{"auth", "logout", "--auth-file", authFile})
	if code != 0 {
		t.Fatalf("auth logout code = %d, output:\n%s", code, out.String())
	}

	code = New(&bytes.Buffer{}, &bytes.Buffer{}).Run([]string{"auth", "status", "--auth-file", authFile})
	if code == 0 {
		t.Fatal("auth status should fail after logout")
	}
}
