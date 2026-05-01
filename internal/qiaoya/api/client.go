package api

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

type Client struct {
	BaseURL     string
	BearerToken string
	HTTP        *http.Client
}

type PageRequest struct {
	Page int
	Size int
}

type Overview struct {
	About        any               `json:"about,omitempty"`
	Stats        any               `json:"stats,omitempty"`
	Courses      any               `json:"courses,omitempty"`
	Plans        any               `json:"plans,omitempty"`
	Services     any               `json:"services,omitempty"`
	Testimonials any               `json:"testimonials,omitempty"`
	UpdateLogs   any               `json:"updateLogs,omitempty"`
	Errors       map[string]string `json:"errors,omitempty"`
}

func NewClient(baseURL string) *Client {
	return &Client{
		BaseURL: strings.TrimRight(baseURL, "/"),
		HTTP: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

func (c *Client) PublicOverview() (Overview, error) {
	var overview Overview
	errs := map[string]string{}

	assign := func(name string, value any, err error) {
		if err != nil {
			errs[name] = err.Error()
			return
		}
		switch name {
		case "about":
			overview.About = value
		case "stats":
			overview.Stats = value
		case "courses":
			overview.Courses = value
		case "plans":
			overview.Plans = value
		case "services":
			overview.Services = value
		case "testimonials":
			overview.Testimonials = value
		case "updateLogs":
			overview.UpdateLogs = value
		}
	}

	value, err := c.GetAbout()
	assign("about", value, err)
	value, err = c.GetStats()
	assign("stats", value, err)
	value, err = c.ListPublicCourses(PageRequest{Page: 1, Size: 100})
	assign("courses", value, err)
	value, err = c.GetPlans()
	assign("plans", value, err)
	value, err = c.GetServices()
	assign("services", value, err)
	value, err = c.GetTestimonials()
	assign("testimonials", value, err)
	if c.BearerToken != "" {
		value, err = c.GetUpdateLogs()
		assign("updateLogs", value, err)
	}

	if len(errs) > 0 {
		overview.Errors = errs
	}
	if overview.About == nil && overview.Stats == nil && overview.Courses == nil && overview.Plans == nil && overview.Services == nil && overview.Testimonials == nil && overview.UpdateLogs == nil {
		return overview, fmt.Errorf("公开信息查询全部失败")
	}
	return overview, nil
}

func (c *Client) GetAbout() (any, error) {
	return c.get("/api/public/site/about")
}

func (c *Client) GetStats() (any, error) {
	return c.get("/api/public/stats/users")
}

func (c *Client) ListPublicCourses(req PageRequest) (any, error) {
	req = normalizePage(req, 1, 20)
	return c.post("/api/public/courses/queries", map[string]any{
		"pageNum":  req.Page,
		"pageSize": req.Size,
	})
}

func (c *Client) GetPlans() (any, error) {
	return c.get("/api/public/subscription-plans")
}

func (c *Client) GetAppPlans() (any, error) {
	return c.get("/api/app/subscription-plans")
}

func (c *Client) GetServices() (any, error) {
	return c.get("/api/public/independent-services")
}

func (c *Client) GetTestimonials() (any, error) {
	return c.get("/api/public/testimonials")
}

func (c *Client) GetUpdateLogs() (any, error) {
	return c.get("/api/app/update-logs")
}

func (c *Client) GetAINewsToday() (any, error) {
	return c.get("/api/app/ai-news/today")
}

func (c *Client) GetAINewsHistory(req PageRequest) (any, error) {
	req = normalizePage(req, 1, 10)
	return c.get(fmt.Sprintf("/api/app/ai-news/history?pageNum=%d&pageSize=%d", req.Page, req.Size))
}

func (c *Client) GetAINewsDaily(date string, req PageRequest) (any, error) {
	if strings.TrimSpace(date) == "" {
		return nil, fmt.Errorf("缺少 --date")
	}
	req = normalizePage(req, 1, 10)
	return c.get(fmt.Sprintf("/api/app/ai-news/daily?date=%s&pageNum=%d&pageSize=%d", date, req.Page, req.Size))
}

func normalizePage(req PageRequest, defaultPage, defaultSize int) PageRequest {
	if req.Page <= 0 {
		req.Page = defaultPage
	}
	if req.Size <= 0 {
		req.Size = defaultSize
	}
	return req
}

func (c *Client) get(path string) (any, error) {
	return c.do(http.MethodGet, path, nil)
}

func (c *Client) post(path string, body any) (any, error) {
	return c.do(http.MethodPost, path, body)
}

func (c *Client) do(method, path string, body any) (any, error) {
	var reader io.Reader
	if body != nil {
		payload, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		reader = bytes.NewReader(payload)
	}

	req, err := http.NewRequest(method, c.BaseURL+path, reader)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Accept", "application/json")
	if c.BearerToken != "" {
		req.Header.Set("Authorization", "Bearer "+c.BearerToken)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, strings.TrimSpace(string(raw)))
	}

	var decoded any
	if len(bytes.TrimSpace(raw)) == 0 {
		return nil, nil
	}
	if err := json.Unmarshal(raw, &decoded); err != nil {
		return nil, fmt.Errorf("解析 JSON 失败: %w", err)
	}
	return unwrapResponse(decoded)
}

func unwrapResponse(value any) (any, error) {
	obj, ok := value.(map[string]any)
	if !ok {
		return value, nil
	}

	if codeValue, exists := obj["code"]; exists {
		if !successCode(codeValue) {
			msg := firstString(obj["message"], obj["msg"])
			if msg == "" {
				msg = fmt.Sprintf("业务错误: %v", codeValue)
			}
			return nil, fmt.Errorf("%s", msg)
		}
	}

	if data, exists := obj["data"]; exists {
		return data, nil
	}
	return value, nil
}

func successCode(value any) bool {
	switch v := value.(type) {
	case nil:
		return true
	case float64:
		return v == 0 || v == 200
	case string:
		return v == "" || v == "0" || v == "200"
	default:
		return false
	}
}

func firstString(values ...any) string {
	for _, value := range values {
		if s, ok := value.(string); ok && strings.TrimSpace(s) != "" {
			return s
		}
	}
	return ""
}
