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

func TestClientGetPublicCourseDetail(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/public/courses/20" {
			http.Error(w, "missing", http.StatusNotFound)
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]any{
			"code": 200,
			"data": map[string]any{
				"id":    "20",
				"title": "AI 专栏",
				"chapters": []any{
					map[string]any{"id": "c1", "title": "第一章"},
				},
			},
		})
	}))
	defer server.Close()

	data, err := NewClient(server.URL).GetPublicCourseDetail("20")
	if err != nil {
		t.Fatalf("GetPublicCourseDetail() error = %v", err)
	}
	obj, ok := data.(map[string]any)
	if !ok || obj["title"] != "AI 专栏" {
		t.Fatalf("unexpected detail: %#v", data)
	}
}
