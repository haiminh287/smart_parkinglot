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
                    if (!string.IsNullOrEmpty(rawCookie))
                    {
                        sessionCookie = rawCookie.Split(';')[0].Trim();
                    }

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
            currentUser = null;
            Debug.Log("[AuthManager] Logged out");
        }

        public void ApplyAuth(UnityWebRequest request, bool isAiService = false)
        {
            if (isAiService)
            {
                request.SetRequestHeader("X-Gateway-Secret", config.gatewaySecret);
            }
            else if (IsAuthenticated)
            {
                request.SetRequestHeader("Cookie", sessionCookie);
            }
            request.SetRequestHeader("Content-Type", "application/json");
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
