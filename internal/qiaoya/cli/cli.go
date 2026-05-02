package cli

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/xhyqaq/qiaoya-cli/internal/qiaoya/api"
	"github.com/xhyqaq/qiaoya-cli/internal/qiaoya/auth"
	"github.com/xhyqaq/qiaoya-cli/internal/qiaoya/installers"
	"github.com/xhyqaq/qiaoya-cli/internal/qiaoya/metadata"
)

type App struct {
	Stdout io.Writer
	Stderr io.Writer
}

type globalOptions struct {
	JSON    bool
	BaseURL string
}

type apiCommandOptions struct {
	Method   string
	Path     string
	Body     string
	BodyFile string
	NoLogin  bool
}

type versionReport struct {
	CurrentVersion  string `json:"currentVersion"`
	CurrentCommit   string `json:"currentCommit"`
	CurrentDate     string `json:"currentDate"`
	LatestVersion   string `json:"latestVersion,omitempty"`
	LatestCommit    string `json:"latestCommit,omitempty"`
	LatestDate      string `json:"latestDate,omitempty"`
	UpdateAvailable bool   `json:"updateAvailable"`
	InstallCommand  string `json:"installCommand"`
	CheckError      string `json:"checkError,omitempty"`
}

type latestVersionManifest struct {
	Version         string `json:"version"`
	Commit          string `json:"commit,omitempty"`
	Date            string `json:"date,omitempty"`
	DownloadBaseURL string `json:"downloadBaseUrl,omitempty"`
	InstallCommand  string `json:"installCommand,omitempty"`
}

func New(stdout, stderr io.Writer) App {
	if stdout == nil {
		stdout = io.Discard
	}
	if stderr == nil {
		stderr = io.Discard
	}
	return App{Stdout: stdout, Stderr: stderr}
}

func (a App) Run(args []string) int {
	globals, rest, err := parseGlobals(args)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 2
	}
	if len(rest) == 0 {
		a.printHelp()
		return 0
	}

	switch rest[0] {
	case "help", "-h", "--help":
		a.printHelp()
		return 0
	case "version", "--version":
		return a.runVersion(rest[1:], globals)
	case "install":
		return a.runInstall(rest[1:], globals)
	case "auth":
		return a.runAuth(rest[1:], globals)
	case "doctor":
		return a.runDoctor(rest[1:], globals)
	case "uninstall":
		return a.runUninstall(rest[1:], globals)
	case "update":
		return a.runUpdate(rest[1:], globals)
	case "public":
		return a.runPublic(rest[1:], globals)
	case "ai-news":
		return a.runAINews(rest[1:], globals)
	case "api":
		return a.runAPI(rest[1:], globals)
	default:
		fmt.Fprintf(a.Stderr, "未知命令: %s\n\n", rest[0])
		a.printHelp()
		return 2
	}
}

func parseGlobals(args []string) (globalOptions, []string, error) {
	options := globalOptions{BaseURL: metadata.DefaultBaseURL}
	var rest []string

	for i := 0; i < len(args); i++ {
		arg := args[i]
		if arg == "--json" {
			options.JSON = true
			continue
		}
		if arg == "--base-url" {
			i++
			if i >= len(args) {
				return options, nil, fmt.Errorf("缺少 --base-url 参数")
			}
			options.BaseURL = strings.TrimRight(args[i], "/")
			continue
		}
		if strings.HasPrefix(arg, "--base-url=") {
			options.BaseURL = strings.TrimRight(strings.TrimPrefix(arg, "--base-url="), "/")
			continue
		}
		rest = append(rest, arg)
		rest = append(rest, args[i+1:]...)
		break
	}
	if strings.TrimSpace(options.BaseURL) == "" {
		options.BaseURL = metadata.DefaultBaseURL
	}
	return options, rest, nil
}

func (a App) printHelp() {
	fmt.Fprintf(a.Stdout, `qiaoya - 敲鸭社区 agent skill 安装器与公开信息 runtime

Usage:
  qiaoya install [--agents auto|all|codex,claude,cursor,windsurf,openclaw] [--project-dir <path>]
  qiaoya doctor [--agents auto|all|...]
  qiaoya auth login
  qiaoya auth status
  qiaoya auth logout
  qiaoya --json version
  qiaoya uninstall [--agents auto|all|...]
  qiaoya --json public overview
  qiaoya --json public courses
  qiaoya --json public chapters --course-id <id>
  qiaoya --json ai-news today
  qiaoya --json api GET /api/app/chapters/latest
  qiaoya --json api POST /api/app/posts/queries --body '{"pageNum":1,"pageSize":10}'

Global options:
  --json                 输出 JSON，推荐 agent 使用
  --base-url <url>       API 地址，默认 %s

`, metadata.DefaultBaseURL)
}

func (a App) runInstall(args []string, globals globalOptions) int {
	options, err := parseInstallOptions(args)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 2
	}
	results, err := installers.Install(options)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 1
	}
	return a.printResults(results, globals.JSON)
}

func (a App) runAuth(args []string, globals globalOptions) int {
	if len(args) == 0 || args[0] == "--help" || args[0] == "-h" {
		fmt.Fprintln(a.Stdout, "Usage: qiaoya auth login|status|logout")
		return 0
	}

	switch args[0] {
	case "login":
		return a.runAuthLogin(args[1:], globals)
	case "status":
		return a.runAuthStatus(args[1:], globals)
	case "logout":
		return a.runAuthLogout(args[1:], globals)
	default:
		fmt.Fprintf(a.Stderr, "未知 auth 子命令: %s\n", args[0])
		return 2
	}
}

func (a App) runAuthLogin(args []string, globals globalOptions) int {
	fs := flag.NewFlagSet("auth login", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	clientID := fs.String("client-id", auth.DefaultClientID, "OAuth2 client id")
	scope := fs.String("scope", auth.DefaultScope, "OAuth2 scope")
	timeout := fs.Duration("timeout", 2*time.Minute, "等待浏览器授权超时时间")
	noBrowser := fs.Bool("no-browser", false, "只打印授权链接，不自动打开浏览器")
	authFile := fs.String("auth-file", "", "登录凭据文件")
	if err := fs.Parse(args); err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 2
	}

	storePath := normalizeAuthFile(*authFile)
	result, err := auth.Login(context.Background(), auth.LoginOptions{
		BaseURL:     globals.BaseURL,
		ClientID:    *clientID,
		Scope:       *scope,
		StorePath:   storePath,
		Timeout:     *timeout,
		OpenBrowser: !*noBrowser,
		Stdout:      a.Stdout,
	})
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 1
	}
	if globals.JSON {
		return a.printJSON(result)
	}
	fmt.Fprintf(a.Stdout, "登录成功，凭据已保存到 %s\n", result.StorePath)
	if !result.ExpiresAt.IsZero() {
		fmt.Fprintf(a.Stdout, "Access token 过期时间: %s\n", result.ExpiresAt.Format(time.RFC3339))
	}
	return 0
}

func (a App) runAuthStatus(args []string, globals globalOptions) int {
	authFile, err := parseAuthFileFlag("auth status", args)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 2
	}
	storePath := normalizeAuthFile(authFile)
	status := auth.LoadStatus(storePath)
	if status.LoggedIn && status.Expired && status.Refreshable {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if _, refreshErr := auth.Refresh(ctx, storePath); refreshErr == nil {
			status = auth.LoadStatus(storePath)
		}
	}
	if globals.JSON {
		return a.printJSON(status)
	}
	if !status.LoggedIn {
		fmt.Fprintf(a.Stdout, "未登录: %s\n", status.StorePath)
		return 1
	}
	fmt.Fprintf(a.Stdout, "已登录: %s\n", status.ClientID)
	fmt.Fprintf(a.Stdout, "API: %s\n", status.BaseURL)
	fmt.Fprintf(a.Stdout, "Scope: %s\n", status.Scope)
	if !status.ExpiresAt.IsZero() {
		fmt.Fprintf(a.Stdout, "Access token 过期时间: %s\n", status.ExpiresAt.Format(time.RFC3339))
	}
	if status.Expired {
		if status.Refreshable {
			fmt.Fprintln(a.Stdout, "状态: Access token 已过期，自动刷新失败，请重新登录")
		} else {
			fmt.Fprintln(a.Stdout, "状态: 已过期，请重新登录")
		}
		return 1
	}
	return 0
}

func (a App) runAuthLogout(args []string, globals globalOptions) int {
	authFile, err := parseAuthFileFlag("auth logout", args)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 2
	}
	storePath := normalizeAuthFile(authFile)
	if err := auth.Logout(storePath); err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 1
	}
	result := map[string]any{"loggedOut": true, "storePath": storePath}
	if globals.JSON {
		return a.printJSON(result)
	}
	fmt.Fprintf(a.Stdout, "已退出登录: %s\n", storePath)
	return 0
}

func (a App) runDoctor(args []string, globals globalOptions) int {
	options, err := parseInstallOptions(args)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 2
	}
	report := installers.Doctor(options)
	if globals.JSON {
		return a.printJSON(report)
	}
	fmt.Fprintf(a.Stdout, "qiaoya: %s\n", report.Version)
	fmt.Fprintf(a.Stdout, "runtime: %s [%s]\n", report.BinaryPath, okText(report.BinaryOK))
	for _, item := range report.AgentChecks {
		fmt.Fprintf(a.Stdout, "%s: %s %s\n", item.Agent, item.Status, item.Path)
		if item.Message != "" {
			fmt.Fprintf(a.Stdout, "  %s\n", item.Message)
		}
	}
	if !report.BinaryOK {
		return 1
	}
	return 0
}

func (a App) runUninstall(args []string, globals globalOptions) int {
	options, err := parseInstallOptions(args)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 2
	}
	results, err := installers.Uninstall(options)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 1
	}
	return a.printResults(results, globals.JSON)
}

func (a App) runVersion(_ []string, globals globalOptions) int {
	if globals.JSON {
		return a.printJSON(buildVersionReport(globals))
	}
	fmt.Fprintf(a.Stdout, "qiaoya %s (%s %s)\n", metadata.Version, metadata.Commit, metadata.Date)
	return 0
}

func (a App) runUpdate(_ []string, globals globalOptions) int {
	report := buildVersionReport(globals)
	if globals.JSON {
		return a.printJSON(report)
	}
	if report.CheckError != "" {
		fmt.Fprintf(a.Stdout, "无法检查最新版本: %s\n", report.CheckError)
		fmt.Fprintf(a.Stdout, "可以重新执行一行安装命令完成更新:\n  %s\n", report.InstallCommand)
		return 0
	}
	if report.UpdateAvailable {
		fmt.Fprintf(a.Stdout, "发现新版本 %s，当前版本 %s。\n", report.LatestVersion, report.CurrentVersion)
		fmt.Fprintf(a.Stdout, "更新命令:\n  %s\n", report.InstallCommand)
		return 0
	}
	fmt.Fprintf(a.Stdout, "当前已是最新版本: %s\n", report.CurrentVersion)
	return 0
}

func buildVersionReport(globals globalOptions) versionReport {
	report := versionReport{
		CurrentVersion: metadata.Version,
		CurrentCommit:  metadata.Commit,
		CurrentDate:    metadata.Date,
		InstallCommand: "curl -fsSL " + metadata.DefaultInstallURL + " | sh",
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	latest, err := fetchLatestVersion(ctx, globals.BaseURL)
	if err != nil {
		report.CheckError = err.Error()
		return report
	}
	report.LatestVersion = latest.Version
	report.LatestCommit = latest.Commit
	report.LatestDate = latest.Date
	if strings.TrimSpace(latest.InstallCommand) != "" {
		report.InstallCommand = strings.TrimSpace(latest.InstallCommand)
	}
	report.UpdateAvailable = compareVersions(latest.Version, metadata.Version) > 0
	return report
}

func fetchLatestVersion(ctx context.Context, baseURL string) (latestVersionManifest, error) {
	endpoint := strings.TrimRight(baseURL, "/") + "/downloads/qiaoya/latest/version.json"
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return latestVersionManifest{}, err
	}
	req.Header.Set("Accept", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return latestVersionManifest{}, err
	}
	defer resp.Body.Close()
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return latestVersionManifest{}, fmt.Errorf("版本检查失败: HTTP %d", resp.StatusCode)
	}
	var latest latestVersionManifest
	if err := json.NewDecoder(resp.Body).Decode(&latest); err != nil {
		return latestVersionManifest{}, fmt.Errorf("解析 version.json 失败: %w", err)
	}
	if strings.TrimSpace(latest.Version) == "" {
		return latestVersionManifest{}, fmt.Errorf("version.json 缺少 version")
	}
	return latest, nil
}

func compareVersions(left, right string) int {
	leftParts, leftOK := parseVersionParts(left)
	rightParts, rightOK := parseVersionParts(right)
	if !leftOK || !rightOK {
		return 0
	}
	for i := 0; i < len(leftParts); i++ {
		if leftParts[i] > rightParts[i] {
			return 1
		}
		if leftParts[i] < rightParts[i] {
			return -1
		}
	}
	return 0
}

func parseVersionParts(value string) ([3]int, bool) {
	var parts [3]int
	value = strings.TrimSpace(strings.TrimPrefix(value, "v"))
	if value == "" || value == "dev" {
		return parts, false
	}
	clean := value
	for i, r := range value {
		if (r < '0' || r > '9') && r != '.' {
			clean = value[:i]
			break
		}
	}
	chunks := strings.Split(clean, ".")
	if len(chunks) == 0 {
		return parts, false
	}
	for i := 0; i < len(parts) && i < len(chunks); i++ {
		if chunks[i] == "" {
			return parts, false
		}
		number, err := strconv.Atoi(chunks[i])
		if err != nil {
			return parts, false
		}
		parts[i] = number
	}
	return parts, true
}

func parseInstallOptions(args []string) (installers.Options, error) {
	fs := flag.NewFlagSet("install", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	agents := fs.String("agents", "auto", "agent list")
	projectDir := fs.String("project-dir", "", "project directory for Cursor/Windsurf rules")
	codexHome := fs.String("codex-home", "", "Codex home")
	claudeHome := fs.String("claude-home", "", "Claude home")
	binDir := fs.String("bin-dir", "", "qiaoya binary directory")
	dryRun := fs.Bool("dry-run", false, "print without writing")
	if err := fs.Parse(args); err != nil {
		return installers.Options{}, err
	}
	return installers.Options{
		Agents:     []string{*agents},
		ProjectDir: *projectDir,
		CodexHome:  *codexHome,
		ClaudeHome: *claudeHome,
		BinDir:     *binDir,
		DryRun:     *dryRun,
	}, nil
}

func parseAuthFileFlag(name string, args []string) (string, error) {
	fs := flag.NewFlagSet(name, flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	authFile := fs.String("auth-file", "", "登录凭据文件")
	if err := fs.Parse(args); err != nil {
		return "", err
	}
	return *authFile, nil
}

func normalizeAuthFile(path string) string {
	if strings.TrimSpace(path) != "" {
		return path
	}
	home, _ := os.UserHomeDir()
	return auth.DefaultStorePath(home)
}

func loadStoredAuthToken(baseURL string) (auth.Token, bool) {
	storePath := normalizeAuthFile("")
	token, err := auth.LoadToken(storePath)
	if err != nil || token.Expired() {
		if err == nil {
			ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			if refreshed, refreshErr := auth.Refresh(ctx, storePath); refreshErr == nil {
				token = refreshed
			} else {
				return auth.Token{}, false
			}
		}
	}
	if token.NeedsRefresh(60 * time.Second) {
		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if refreshed, refreshErr := auth.Refresh(ctx, storePath); refreshErr == nil {
			token = refreshed
		}
	}
	if token.Expired() {
		return auth.Token{}, false
	}
	if strings.TrimRight(token.BaseURL, "/") != strings.TrimRight(baseURL, "/") {
		return auth.Token{}, false
	}
	return token, true
}

func attachStoredAuth(client *api.Client) {
	token, ok := loadStoredAuthToken(client.BaseURL)
	if !ok {
		return
	}
	client.BearerToken = token.AccessToken
}

func (a App) runPublic(args []string, globals globalOptions) int {
	if len(args) == 0 || args[0] == "--help" || args[0] == "-h" {
		fmt.Fprintln(a.Stdout, "Usage: qiaoya --json public overview|about|stats|courses|course|chapters|plans|services|testimonials|update-logs")
		return 0
	}

	client := api.NewClient(globals.BaseURL)
	attachStoredAuth(client)
	var data any
	var err error
	switch args[0] {
	case "overview":
		data, err = client.PublicOverview()
	case "about":
		data, err = client.GetAbout()
	case "stats":
		data, err = client.GetStats()
	case "courses", "course-list":
		req, parseErr := parsePageArgs(args[1:], 1, 20)
		if parseErr != nil {
			fmt.Fprintln(a.Stderr, parseErr)
			return 2
		}
		data, err = client.ListPublicCourses(req)
	case "course", "course-detail":
		id, parseErr := parseStringFlag(args[1:], "id", "course id")
		if parseErr != nil {
			fmt.Fprintln(a.Stderr, parseErr)
			return 2
		}
		data, err = client.GetPublicCourseDetail(id)
	case "chapters", "course-chapters":
		courseID, parseErr := parseStringFlag(args[1:], "course-id", "course id")
		if parseErr != nil {
			fmt.Fprintln(a.Stderr, parseErr)
			return 2
		}
		var course any
		course, err = client.GetPublicCourseDetail(courseID)
		if err == nil {
			data, err = publicCourseChapters(course)
		}
	case "plans":
		data, err = client.GetPlans()
	case "app-plans":
		data, err = client.GetAppPlans()
	case "services":
		data, err = client.GetServices()
	case "testimonials":
		data, err = client.GetTestimonials()
	case "update-logs":
		if client.BearerToken == "" {
			fmt.Fprintln(a.Stderr, "查看更新日志需要先通过浏览器授权登录：qiaoya auth login")
			return 1
		}
		data, err = client.GetUpdateLogs()
	default:
		fmt.Fprintf(a.Stderr, "未知 public 子命令: %s\n", args[0])
		return 2
	}
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 1
	}
	return a.printData(data, globals.JSON)
}

func (a App) runAINews(args []string, globals globalOptions) int {
	if len(args) == 0 || args[0] == "--help" || args[0] == "-h" {
		fmt.Fprintln(a.Stdout, "Usage: qiaoya --json ai-news today|history|daily --date YYYY-MM-DD")
		return 0
	}

	client := api.NewClient(globals.BaseURL)
	attachStoredAuth(client)
	var data any
	var err error
	switch args[0] {
	case "today":
		data, err = client.GetAINewsToday()
	case "history":
		req, parseErr := parsePageArgs(args[1:], 1, 10)
		if parseErr != nil {
			fmt.Fprintln(a.Stderr, parseErr)
			return 2
		}
		data, err = client.GetAINewsHistory(req)
	case "daily":
		fs := flag.NewFlagSet("daily", flag.ContinueOnError)
		fs.SetOutput(io.Discard)
		date := fs.String("date", "", "date")
		page := fs.Int("page", 1, "page")
		size := fs.Int("size", 10, "size")
		if err := fs.Parse(args[1:]); err != nil {
			fmt.Fprintln(a.Stderr, err)
			return 2
		}
		data, err = client.GetAINewsDaily(*date, api.PageRequest{Page: *page, Size: *size})
	default:
		fmt.Fprintf(a.Stderr, "未知 ai-news 子命令: %s\n", args[0])
		return 2
	}
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 1
	}
	return a.printData(data, globals.JSON)
}

func (a App) runAPI(args []string, globals globalOptions) int {
	options, err := parseAPICommandOptions(args)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 2
	}
	if !isAllowedFrontendAPIPath(options.Path) {
		fmt.Fprintf(a.Stderr, "不允许调用该 API path: %s\n", options.Path)
		return 2
	}

	body, err := parseAPIBody(options.Body, options.BodyFile)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 2
	}

	client := api.NewClient(globals.BaseURL)
	token, hasToken := loadStoredAuthToken(globals.BaseURL)
	if hasToken {
		client.BearerToken = token.AccessToken
	}
	loginRequired := !hasToken || (requiresWriteScope(options.Method, options.Path) && !hasScope(token.Scope, "write"))
	if loginRequired && !options.NoLogin && requiresLoginAPIPath(options.Path) {
		if err := a.loginForAPI(globals); err != nil {
			fmt.Fprintln(a.Stderr, err)
			return 1
		}
		client = api.NewClient(globals.BaseURL)
		if refreshedToken, ok := loadStoredAuthToken(globals.BaseURL); ok {
			client.BearerToken = refreshedToken.AccessToken
		}
	}

	data, err := client.Call(options.Method, options.Path, body)
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 1
	}
	return a.printData(data, globals.JSON)
}

func parsePageArgs(args []string, defaultPage, defaultSize int) (api.PageRequest, error) {
	fs := flag.NewFlagSet("page", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	page := fs.Int("page", defaultPage, "page")
	size := fs.Int("size", defaultSize, "size")
	if err := fs.Parse(args); err != nil {
		return api.PageRequest{}, err
	}
	return api.PageRequest{Page: *page, Size: *size}, nil
}

func parseAPICommandOptions(args []string) (apiCommandOptions, error) {
	if len(args) == 0 || args[0] == "--help" || args[0] == "-h" {
		return apiCommandOptions{}, fmt.Errorf("Usage: qiaoya --json api METHOD /api/path [--body JSON|--body-file path] [--no-login]")
	}
	if len(args) < 2 {
		return apiCommandOptions{}, fmt.Errorf("Usage: qiaoya --json api METHOD /api/path [--body JSON|--body-file path] [--no-login]")
	}
	options := apiCommandOptions{
		Method: strings.ToUpper(strings.TrimSpace(args[0])),
		Path:   strings.TrimSpace(args[1]),
	}
	fs := flag.NewFlagSet("api", flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	fs.StringVar(&options.Body, "body", "", "JSON request body")
	fs.StringVar(&options.BodyFile, "body-file", "", "file containing JSON request body")
	fs.BoolVar(&options.NoLogin, "no-login", false, "do not open browser login automatically")
	if err := fs.Parse(args[2:]); err != nil {
		return apiCommandOptions{}, err
	}
	switch options.Method {
	case "GET", "POST", "PUT", "PATCH", "DELETE":
	default:
		return apiCommandOptions{}, fmt.Errorf("不支持的 HTTP method: %s", options.Method)
	}
	if options.Path == "" || !strings.HasPrefix(options.Path, "/api/") {
		return apiCommandOptions{}, fmt.Errorf("API path 必须以 /api/ 开头")
	}
	if options.Body != "" && options.BodyFile != "" {
		return apiCommandOptions{}, fmt.Errorf("--body 和 --body-file 不能同时使用")
	}
	return options, nil
}

func parseAPIBody(body, bodyFile string) (any, error) {
	if strings.TrimSpace(bodyFile) != "" {
		raw, err := os.ReadFile(bodyFile)
		if err != nil {
			return nil, err
		}
		body = string(raw)
	}
	if strings.TrimSpace(body) == "" {
		return nil, nil
	}
	var decoded any
	if err := json.Unmarshal([]byte(body), &decoded); err != nil {
		return nil, fmt.Errorf("解析 --body JSON 失败: %w", err)
	}
	return decoded, nil
}

func isAllowedFrontendAPIPath(path string) bool {
	path = stripQuery(path)
	if isBlockedFrontendAPIPath(path) {
		return false
	}
	if path == "/api/user" || path == "/api/expressions" || path == "/api/testimonials" || path == "/api/interview-questions" {
		return true
	}
	allowedPrefixes := []string{
		"/api/public/",
		"/api/app/",
		"/api/user/",
		"/api/expressions/",
		"/api/likes/",
		"/api/favorites/",
		"/api/reactions/",
		"/api/testimonials/",
		"/api/interview-questions/",
	}
	for _, prefix := range allowedPrefixes {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}
	return false
}

func isBlockedFrontendAPIPath(path string) bool {
	if path == "/api/public/oss-callback" {
		return true
	}
	blockedPrefixes := []string{
		"/api/admin/",
		"/api/auth/",
		"/api/public/oauth2/",
		"/api/public/oauth/github/",
		"/api/public/cdn/",
	}
	for _, prefix := range blockedPrefixes {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}
	return false
}

func requiresLoginAPIPath(path string) bool {
	path = stripQuery(path)
	if strings.HasPrefix(path, "/api/public/resource/") && strings.HasSuffix(path, "/access") {
		return true
	}
	return !strings.HasPrefix(path, "/api/public/")
}

func stripQuery(path string) string {
	if i := strings.IndexByte(path, '?'); i >= 0 {
		return path[:i]
	}
	return path
}

func requiresWriteScope(method, path string) bool {
	path = stripQuery(path)
	switch strings.ToUpper(strings.TrimSpace(method)) {
	case "PUT", "PATCH", "DELETE":
		return true
	case "POST":
		return !isReadOnlyPostPath(path)
	default:
		return false
	}
}

func isReadOnlyPostPath(path string) bool {
	if strings.HasPrefix(path, "/api/public/") {
		return true
	}
	if strings.HasSuffix(path, "/queries") {
		return true
	}
	switch path {
	case "/api/likes/status/batch",
		"/api/likes/count/batch",
		"/api/favorites/status/batch",
		"/api/app/follows/batch-check":
		return true
	default:
		return false
	}
}

func hasScope(scope, required string) bool {
	required = strings.TrimSpace(required)
	if required == "" {
		return true
	}
	for _, item := range strings.Fields(scope) {
		if item == required {
			return true
		}
	}
	return false
}

func (a App) loginForAPI(globals globalOptions) error {
	_, err := auth.Login(context.Background(), auth.LoginOptions{
		BaseURL:     globals.BaseURL,
		ClientID:    auth.DefaultClientID,
		Scope:       auth.DefaultScope,
		StorePath:   normalizeAuthFile(""),
		Timeout:     2 * time.Minute,
		OpenBrowser: true,
		Stdout:      a.Stderr,
	})
	return err
}

func parseStringFlag(args []string, name, label string) (string, error) {
	fs := flag.NewFlagSet(name, flag.ContinueOnError)
	fs.SetOutput(io.Discard)
	value := fs.String(name, "", label)
	if err := fs.Parse(args); err != nil {
		return "", err
	}
	if strings.TrimSpace(*value) == "" {
		return "", fmt.Errorf("缺少 --%s", name)
	}
	return strings.TrimSpace(*value), nil
}

func publicCourseChapters(course any) (any, error) {
	obj, ok := course.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("课程详情格式异常")
	}
	chapters, ok := obj["chapters"]
	if !ok {
		return nil, fmt.Errorf("课程详情中没有 chapters 字段")
	}
	return map[string]any{
		"courseId":   obj["id"],
		"courseName": obj["title"],
		"chapters":   chapters,
	}, nil
}

func (a App) printResults(results []installers.Result, asJSON bool) int {
	if asJSON {
		return a.printJSON(results)
	}
	exit := 0
	for _, item := range results {
		fmt.Fprintf(a.Stdout, "%s: %s %s\n", item.Agent, item.Status, item.Path)
		if item.Message != "" {
			fmt.Fprintf(a.Stdout, "  %s\n", item.Message)
		}
		if item.Status == "failed" {
			exit = 1
		}
	}
	return exit
}

func (a App) printData(data any, asJSON bool) int {
	if asJSON {
		return a.printJSON(data)
	}
	raw, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 1
	}
	fmt.Fprintln(a.Stdout, string(raw))
	return 0
}

func (a App) printJSON(data any) int {
	raw, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		fmt.Fprintln(a.Stderr, err)
		return 1
	}
	fmt.Fprintln(a.Stdout, string(raw))
	return 0
}

func okText(ok bool) string {
	if ok {
		return "ok"
	}
	return "missing"
}

func Main() {
	app := New(os.Stdout, os.Stderr)
	os.Exit(app.Run(os.Args[1:]))
}
