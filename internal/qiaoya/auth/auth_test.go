package auth

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestRefreshRotatesAndStoresToken(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/public/oauth2/token" {
			t.Fatalf("unexpected path: %s", r.URL.Path)
		}
		if err := r.ParseForm(); err != nil {
			t.Fatal(err)
		}
		if got := r.Form.Get("grant_type"); got != "refresh_token" {
			t.Fatalf("grant_type = %q", got)
		}
		if got := r.Form.Get("client_id"); got != DefaultClientID {
			t.Fatalf("client_id = %q", got)
		}
		if got := r.Form.Get("refresh_token"); got != "old-refresh" {
			t.Fatalf("refresh_token = %q", got)
		}
		_ = json.NewEncoder(w).Encode(Token{
			AccessToken:  "new-access",
			TokenType:    "Bearer",
			ExpiresIn:    3600,
			RefreshToken: "new-refresh",
			Scope:        DefaultScope,
		})
	}))
	defer server.Close()

	storePath := t.TempDir() + "/auth.json"
	err := SaveToken(storePath, Token{
		AccessToken:  "old-access",
		TokenType:    "Bearer",
		ExpiresIn:    1,
		RefreshToken: "old-refresh",
		Scope:        DefaultScope,
		BaseURL:      server.URL,
		ClientID:     DefaultClientID,
		ObtainedAt:   time.Now().Add(-time.Hour),
	})
	if err != nil {
		t.Fatal(err)
	}

	token, err := Refresh(context.Background(), storePath)
	if err != nil {
		t.Fatal(err)
	}
	if token.AccessToken != "new-access" || token.RefreshToken != "new-refresh" {
		t.Fatalf("unexpected refreshed token: %#v", token)
	}

	stored, err := LoadToken(storePath)
	if err != nil {
		t.Fatal(err)
	}
	if stored.AccessToken != "new-access" || stored.RefreshToken != "new-refresh" {
		t.Fatalf("unexpected stored token: %#v", stored)
	}
	if !strings.EqualFold(stored.BaseURL, server.URL) || stored.ClientID != DefaultClientID {
		t.Fatalf("metadata not preserved: %#v", stored)
	}
}
