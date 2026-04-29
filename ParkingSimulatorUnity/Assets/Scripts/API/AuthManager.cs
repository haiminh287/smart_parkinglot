using System;
using System.Collections;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;

namespace ParkingSim.API
{
    public class AuthManager : MonoBehaviour
    {
        public static AuthManager Instance { get; private set; }

        [SerializeField] private ApiConfig config;

        private string sessionCookie;
        private string csrfToken;
        private LoginResponse currentUser;

        public bool IsAuthenticated => !string.IsNullOrEmpty(sessionCookie);
        public string SessionCookie => sessionCookie;
        public LoginResponse CurrentUser => currentUser;

        public event Action OnLoginSuccess;
        public event Action<string> OnLoginFailed;

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            if (transform.parent == null)
                DontDestroyOnLoad(gameObject);

            if (config == null)
                config = Resources.Load<ApiConfig>("ApiConfig");
        }

        public IEnumerator Login(string email, string password)
        {
            string url = $"{config.gatewayBaseUrl}/api/auth/login/";
            string json = JsonConvert.SerializeObject(new { email, password });
            byte[] bodyRaw = Encoding.UTF8.GetBytes(json);

            using (var request = new UnityWebRequest(url, "POST"))
            {
                request.uploadHandler = new UploadHandlerRaw(bodyRaw);
                request.downloadHandler = new DownloadHandlerBuffer();
                request.SetRequestHeader("Content-Type", "application/json");

                yield return request.SendWebRequest();

                if (request.result == UnityWebRequest.Result.Success)
                {
                    string rawCookie = request.GetResponseHeader("Set-Cookie");
                    ParseSetCookies(rawCookie);

                    string body = request.downloadHandler.text;
                    currentUser = JsonConvert.DeserializeObject<LoginResponse>(body);

                    string cookiePreview = sessionCookie != null && sessionCookie.Length > 20
                        ? sessionCookie.Substring(0, 20) + "..."
                        : sessionCookie;
                    Debug.Log($"[AuthManager] Login OK – cookie: {cookiePreview}");
                    OnLoginSuccess?.Invoke();
                }
                else
                {
                    string errorBody = request.downloadHandler?.text ?? request.error;
                    string errorMsg = ParseError(errorBody, (int)request.responseCode);
                    Debug.LogWarning($"[AuthManager] Login FAILED: {errorMsg}");
                    OnLoginFailed?.Invoke(errorMsg);
                }
            }
        }

        public void Logout()
        {
            sessionCookie = null;
            csrfToken = null;
            currentUser = null;
            Debug.Log("[AuthManager] Logged out");
        }

        public void ApplyAuth(UnityWebRequest request, bool isAiService = false)
        {
            if (isAiService)
            {
                request.SetRequestHeader("X-Gateway-Secret", config.gatewaySecret);
                if (!string.IsNullOrEmpty(config.esp32DeviceToken))
                    request.SetRequestHeader("X-Device-Token", config.esp32DeviceToken);
            }
            else if (IsAuthenticated)
            {
                string cookieHeader = sessionCookie;
                if (!string.IsNullOrEmpty(csrfToken))
                    cookieHeader += $"; csrftoken={csrfToken}";
                request.SetRequestHeader("Cookie", cookieHeader);
                if (!string.IsNullOrEmpty(csrfToken))
                    request.SetRequestHeader("X-CSRFToken", csrfToken);
            }
            request.SetRequestHeader("Content-Type", "application/json");
        }

        private void ParseSetCookies(string raw)
        {
            if (string.IsNullOrEmpty(raw)) return;

            // Unity may concatenate multiple Set-Cookie headers with commas.
            // Split by comma, then check each segment for known cookie names.
            // Expires dates also contain commas, but we only match known prefixes.
            string[] segments = raw.Split(',');
            foreach (string segment in segments)
            {
                string trimmed = segment.Trim();
                // Take the name=value part before any attributes
                string nameValue = trimmed.Split(';')[0].Trim();

                if (nameValue.StartsWith("session_id=", StringComparison.OrdinalIgnoreCase))
                {
                    sessionCookie = nameValue;
                }
                else if (nameValue.StartsWith("csrftoken=", StringComparison.OrdinalIgnoreCase))
                {
                    int eq = nameValue.IndexOf('=');
                    if (eq >= 0) csrfToken = nameValue.Substring(eq + 1);
                }
            }
        }

        private string ParseError(string body, int statusCode)
        {
            if (string.IsNullOrEmpty(body)) return $"HTTP {statusCode}";
            try
            {
                var err = JsonConvert.DeserializeObject<ApiErrorResponse>(body);
                if (err?.Error != null) return err.Error.Message;
            }
            catch { /* not this format */ }
            try
            {
                var django = JsonConvert.DeserializeObject<DjangoErrorResponse>(body);
                if (!string.IsNullOrEmpty(django?.Detail)) return django.Detail;
                if (!string.IsNullOrEmpty(django?.Error)) return django.Error;
            }
            catch { /* not this format */ }
            return $"HTTP {statusCode}: {body}";
        }
    }
}
