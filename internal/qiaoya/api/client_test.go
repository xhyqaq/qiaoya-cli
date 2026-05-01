package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestClientPublicOverviewCollectsPartialResults(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/api/public/site/about":
			_ = json.NewEncoder(w).Encode(map[string]any{"code": 200, "data": map[string]any{"title": "关于敲鸭"}})
		case "/api/public/stats/users":
			_ = json.NewEncoder(w).Encode(map[string]any{"code": 200, "data": map[string]any{"totalCount": 128}})
		case "/api/public/courses/queries":
			_ = json.NewEncoder(w).Encode(map[string]any{"code": 200, "data": map[string]any{"records": []any{map[string]any{"title": "AI Agent"}}}})
		default:
			http.Error(w, "missing", http.StatusNotFound)
		}
	}))
	defer server.Close()

	client := NewClient(server.URL)
	overview, err := client.PublicOverview()
	if err != nil {
		t.Fatalf("PublicOverview() error = %v", err)
	}
	if overview.About == nil || overview.Stats == nil || overview.Courses == nil {
		t.Fatalf("overview missing expected data: %#v", overview)
	}
	if len(overview.Errors) == 0 {
		t.Fatalf("overview should keep partial errors")
	}
}

func TestClientRejectsBusinessError(t *testing.T) {
	_, err := unwrapResponse(map[string]any{"code": float64(500), "message": "boom"})
	if err == nil {
		t.Fatalf("expected business error")
	}
}
