package auth

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"html"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

const (
	DefaultClientID = "qiaoya-cli"
	DefaultScope    = "openid profile email read write"
)

type LoginOptions struct {
	BaseURL     string
	ClientID    string
	Scope       string
	StorePath   string
	Timeout     time.Duration
	OpenBrowser bool
	Stdout      io.Writer
	OpenURL     func(string) error
}

type LoginResult struct {
	StorePath string
	BaseURL   string
	ClientID  string
	Scope     string
	ExpiresAt time.Time
}

type Token struct {
	AccessToken  string    `json:"access_token"`
	TokenType    string    `json:"token_type"`
	ExpiresIn    int64     `json:"expires_in"`
	RefreshToken string    `json:"refresh_token,omitempty"`
	Scope        string    `json:"scope"`
	BaseURL      string    `json:"base_url"`
	ClientID     string    `json:"client_id"`
	ObtainedAt   time.Time `json:"obtained_at"`
}

type Status struct {
	LoggedIn    bool      `json:"loggedIn"`
	StorePath   string    `json:"storePath"`
	BaseURL     string    `json:"baseUrl,omitempty"`
	ClientID    string    `json:"clientId,omitempty"`
	Scope       string    `json:"scope,omitempty"`
	ExpiresAt   time.Time `json:"expiresAt,omitempty"`
	Expired     bool      `json:"expired,omitempty"`
	Refreshable bool      `json:"refreshable,omitempty"`
}

type callbackResult struct {
	code string
	err  error
}

func DefaultStorePath(home string) string {
	return filepath.Join(home, ".qiaoya", "auth.json")
}

func Login(ctx context.Context, options LoginOptions) (LoginResult, error) {
	options = normalizeLoginOptions(options)

	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return LoginResult{}, fmt.Errorf("启动本地回调端口失败: %w", err)
	}
	defer listener.Close()

	port := listener.Addr().(*net.TCPAddr).Port
	redirectURI := fmt.Sprintf("http://127.0.0.1:%d/callback", port)

	state, err := randomURLToken(32)
	if err != nil {
		return LoginResult{}, err
	}
	codeVerifier, err := randomURLToken(64)
	if err != nil {
		return LoginResult{}, err
	}
	codeChallenge := codeChallengeS256(codeVerifier)

	resultCh := make(chan callbackResult, 1)
	server := &http.Server{Handler: callbackHandler(state, resultCh)}
	go func() {
		if serveErr := server.Serve(listener); serveErr != nil && !errors.Is(serveErr, http.ErrServerClosed) {
			select {
			case resultCh <- callbackResult{err: serveErr}:
			default:
			}
		}
	}()
	defer func() {
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		defer cancel()
		_ = server.Shutdown(shutdownCtx)
	}()

	authURL := buildAuthorizeURL(options.BaseURL, options.ClientID, redirectURI, options.Scope, state, codeChallenge)
	if options.Stdout != nil {
		fmt.Fprintf(options.Stdout, "请在浏览器中完成敲鸭授权：\n%s\n\n", authURL)
	}
	if options.OpenBrowser {
		if err := options.OpenURL(authURL); err != nil && options.Stdout != nil {
			fmt.Fprintf(options.Stdout, "无法自动打开浏览器，请手动打开上面的链接：%v\n\n", err)
		}
	}

	waitCtx := ctx
	if waitCtx == nil {
		waitCtx = context.Background()
	}
	timeoutCtx, cancel := context.WithTimeout(waitCtx, options.Timeout)
	defer cancel()

	var callback callbackResult
	select {
	case callback = <-resultCh:
	case <-timeoutCtx.Done():
		return LoginResult{}, fmt.Errorf("等待浏览器授权超时")
	}
	if callback.err != nil {
		return LoginResult{}, callback.err
	}

	token, err := exchangeCode(timeoutCtx, options.BaseURL, options.ClientID, callback.code, redirectURI, codeVerifier)
	if err != nil {
		return LoginResult{}, err
	}
	token.BaseURL = options.BaseURL
	token.ClientID = options.ClientID
	token.ObtainedAt = time.Now()

	if err := SaveToken(options.StorePath, token); err != nil {
		return LoginResult{}, err
	}

	return LoginResult{
		StorePath: options.StorePath,
		BaseURL:   options.BaseURL,
		ClientID:  options.ClientID,
		Scope:     token.Scope,
		ExpiresAt: token.ExpiresAt(),
	}, nil
}

func LoadStatus(storePath string) Status {
	status := Status{StorePath: storePath}
	token, err := LoadToken(storePath)
	if err != nil {
		return status
	}
	status.LoggedIn = true
	status.BaseURL = token.BaseURL
	status.ClientID = token.ClientID
	status.Scope = token.Scope
	status.ExpiresAt = token.ExpiresAt()
	status.Expired = token.Expired()
	status.Refreshable = strings.TrimSpace(token.RefreshToken) != ""
	return status
}

func Refresh(ctx context.Context, storePath string) (Token, error) {
	token, err := LoadToken(storePath)
	if err != nil {
		return Token{}, err
	}
	if strings.TrimSpace(token.RefreshToken) == "" {
		return Token{}, fmt.Errorf("缺少 refresh_token，请重新登录")
	}
	if strings.TrimSpace(token.BaseURL) == "" || strings.TrimSpace(token.ClientID) == "" {
		return Token{}, fmt.Errorf("登录凭据缺少 OAuth2 client 信息，请重新登录")
	}

	refreshed, err := refreshToken(ctx, token.BaseURL, token.ClientID, token.RefreshToken)
	if err != nil {
		return Token{}, err
	}
	if refreshed.RefreshToken == "" {
		refreshed.RefreshToken = token.RefreshToken
	}
	refreshed.BaseURL = token.BaseURL
	refreshed.ClientID = token.ClientID
	refreshed.ObtainedAt = time.Now()
	if err := SaveToken(storePath, refreshed); err != nil {
		return Token{}, err
	}
	return refreshed, nil
}

func LoadToken(storePath string) (Token, error) {
	raw, err := os.ReadFile(storePath)
	if err != nil {
		return Token{}, err
	}
	var token Token
	if err := json.Unmarshal(raw, &token); err != nil {
		return Token{}, err
	}
	if strings.TrimSpace(token.AccessToken) == "" {
		return Token{}, fmt.Errorf("登录凭据无效")
	}
	return token, nil
}

func SaveToken(storePath string, token Token) error {
	if err := os.MkdirAll(filepath.Dir(storePath), 0o700); err != nil {
		return err
	}
	raw, err := json.MarshalIndent(token, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(storePath, append(raw, '\n'), 0o600)
}

func Logout(storePath string) error {
	if err := os.Remove(storePath); err != nil && !errors.Is(err, os.ErrNotExist) {
		return err
	}
	return nil
}

func (t Token) ExpiresAt() time.Time {
	if t.ExpiresIn <= 0 || t.ObtainedAt.IsZero() {
		return time.Time{}
	}
	return t.ObtainedAt.Add(time.Duration(t.ExpiresIn) * time.Second)
}

func (t Token) Expired() bool {
	expiresAt := t.ExpiresAt()
	return !expiresAt.IsZero() && time.Now().After(expiresAt)
}

func (t Token) NeedsRefresh(window time.Duration) bool {
	expiresAt := t.ExpiresAt()
	return !expiresAt.IsZero() && time.Now().Add(window).After(expiresAt)
}

func normalizeLoginOptions(options LoginOptions) LoginOptions {
	options.BaseURL = strings.TrimRight(strings.TrimSpace(options.BaseURL), "/")
	if options.ClientID == "" {
		options.ClientID = DefaultClientID
	}
	if options.Scope == "" {
		options.Scope = DefaultScope
	}
	if options.Timeout <= 0 {
		options.Timeout = 2 * time.Minute
	}
	if options.OpenURL == nil {
		options.OpenURL = OpenBrowser
	}
	return options
}

func callbackHandler(expectedState string, resultCh chan<- callbackResult) http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/callback", func(w http.ResponseWriter, r *http.Request) {
		query := r.URL.Query()
		if errText := query.Get("error"); errText != "" {
			description := query.Get("error_description")
			writeCallbackPage(w, "授权失败", description)
			sendCallbackResult(resultCh, callbackResult{err: fmt.Errorf("授权失败: %s %s", errText, description)})
			return
		}
		if query.Get("state") != expectedState {
			writeCallbackPage(w, "授权失败", "state 校验失败，请重新登录")
			sendCallbackResult(resultCh, callbackResult{err: fmt.Errorf("state 校验失败")})
			return
		}
		code := query.Get("code")
		if code == "" {
			writeCallbackPage(w, "授权失败", "缺少授权码")
			sendCallbackResult(resultCh, callbackResult{err: fmt.Errorf("缺少授权码")})
			return
		}
		writeCallbackPage(w, "授权成功", "可以回到终端继续使用 qiaoya")
		sendCallbackResult(resultCh, callbackResult{code: code})
	})
	return mux
}

func sendCallbackResult(resultCh chan<- callbackResult, result callbackResult) {
	select {
	case resultCh <- result:
	default:
	}
}

func writeCallbackPage(w http.ResponseWriter, title, message string) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	fmt.Fprintf(w, `<!doctype html><html><head><meta charset="utf-8"><title>%s</title></head><body style="font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;line-height:1.6;padding:40px"><h1>%s</h1><p>%s</p></body></html>`,
		html.EscapeString(title),
		html.EscapeString(title),
		html.EscapeString(message),
	)
}

func buildAuthorizeURL(baseURL, clientID, redirectURI, scope, state, codeChallenge string) string {
	values := url.Values{}
	values.Set("client_id", clientID)
	values.Set("redirect_uri", redirectURI)
	values.Set("response_type", "code")
	values.Set("scope", scope)
	values.Set("state", state)
	values.Set("code_challenge", codeChallenge)
	values.Set("code_challenge_method", "S256")
	return strings.TrimRight(baseURL, "/") + "/api/public/oauth2/authorize?" + values.Encode()
}

func exchangeCode(ctx context.Context, baseURL, clientID, code, redirectURI, codeVerifier string) (Token, error) {
	form := url.Values{}
	form.Set("grant_type", "authorization_code")
	form.Set("client_id", clientID)
	form.Set("code", code)
	form.Set("redirect_uri", redirectURI)
	form.Set("code_verifier", codeVerifier)

	return requestToken(ctx, baseURL, form)
}

func refreshToken(ctx context.Context, baseURL, clientID, refreshToken string) (Token, error) {
	form := url.Values{}
	form.Set("grant_type", "refresh_token")
	form.Set("client_id", clientID)
	form.Set("refresh_token", refreshToken)

	return requestToken(ctx, baseURL, form)
}

func requestToken(ctx context.Context, baseURL string, form url.Values) (Token, error) {
	req, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		strings.TrimRight(baseURL, "/")+"/api/public/oauth2/token",
		strings.NewReader(form.Encode()),
	)
	if err != nil {
		return Token{}, err
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	req.Header.Set("Accept", "application/json")

	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return Token{}, err
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return Token{}, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return Token{}, fmt.Errorf("换取 token 失败: HTTP %d: %s", resp.StatusCode, strings.TrimSpace(string(raw)))
	}

	var token Token
	if err := json.Unmarshal(raw, &token); err != nil {
		return Token{}, fmt.Errorf("解析 token 响应失败: %w", err)
	}
	if strings.TrimSpace(token.AccessToken) == "" {
		return Token{}, fmt.Errorf("token 响应缺少 access_token")
	}
	return token, nil
}

func randomURLToken(byteLen int) (string, error) {
	buf := make([]byte, byteLen)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	return base64.RawURLEncoding.EncodeToString(buf), nil
}

func codeChallengeS256(verifier string) string {
	sum := sha256.Sum256([]byte(verifier))
	return base64.RawURLEncoding.EncodeToString(sum[:])
}

func OpenBrowser(target string) error {
	switch runtime.GOOS {
	case "darwin":
		return exec.Command("open", target).Start()
	case "windows":
		return exec.Command("rundll32", "url.dll,FileProtocolHandler", target).Start()
	default:
		return exec.Command("xdg-open", target).Start()
	}
}
