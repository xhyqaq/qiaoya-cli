package cli

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
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

func TestAPICommandCallsAllowedFrontendEndpoint(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost || r.URL.Path != "/api/public/test" {
			http.Error(w, "missing", http.StatusNotFound)
			return
		}
		var body map[string]any
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			t.Fatalf("decode body: %v", err)
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"code": 200,
			"data": map[string]any{"echo": body["name"]},
		})
	}))
	defer server.Close()

	var out bytes.Buffer
	code := New(&out, &bytes.Buffer{}).Run([]string{
		"--json", "--base-url", server.URL,
		"api", "POST", "/api/public/test", "--body", `{"name":"qiaoya"}`,
	})
	if code != 0 {
		t.Fatalf("api command code = %d, output:\n%s", code, out.String())
	}
	if !strings.Contains(out.String(), "qiaoya") {
		t.Fatalf("api output missing response: %s", out.String())
	}
}

func TestAPICommandRejectsAdminEndpoint(t *testing.T) {
	var stderr bytes.Buffer
	code := New(&bytes.Buffer{}, &stderr).Run([]string{"--json", "api", "GET", "/api/admin/users"})
	if code != 2 {
		t.Fatalf("api admin code = %d, stderr:\n%s", code, stderr.String())
	}
	if !strings.Contains(stderr.String(), "不允许调用") {
		t.Fatalf("api admin stderr = %s", stderr.String())
	}
}

func TestAPIWhitelistIncludesFrontendExpressionEndpoint(t *testing.T) {
	if !isAllowedFrontendAPIPath("/api/expressions/alias-map") {
		t.Fatal("expressions alias endpoint should be allowed")
	}
	if !isAllowedFrontendAPIPath("/api/public/resource/123/access") {
		t.Fatal("public resource access endpoint should be allowed")
	}
	if !requiresLoginAPIPath("/api/public/resource/123/access") {
		t.Fatal("public resource access endpoint should trigger login")
	}
	if isAllowedFrontendAPIPath("/api/auth/login") {
		t.Fatal("password login endpoint should not be allowed")
	}
	if isAllowedFrontendAPIPath("/api/public/oauth2/token") {
		t.Fatal("OAuth token endpoint should not be exposed through api bridge")
	}
	if isAllowedFrontendAPIPath("/api/public/oss-callback") {
		t.Fatal("OSS callback endpoint should not be exposed through api bridge")
	}
}

func TestWriteMethodsRequireWriteScope(t *testing.T) {
	if requiresWriteScope(http.MethodGet, "/api/user/posts") {
		t.Fatal("GET should not require write scope")
	}
	if requiresWriteScope(http.MethodPost, "/api/app/posts/queries") {
		t.Fatal("query POST should not require write scope")
	}
	if !requiresWriteScope(http.MethodPost, "/api/user/comments") {
		t.Fatal("mutating POST should require write scope")
	}
	if !hasScope("openid profile email read write", "write") {
		t.Fatal("write scope should be detected")
	}
	if hasScope("openid profile email read", "write") {
		t.Fatal("read-only token should not satisfy write scope")
	}
}
