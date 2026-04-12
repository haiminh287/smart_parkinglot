using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.TestTools.TestRunner.Api;
using UnityEngine;

namespace ParkingSim.Editor
{
    /// <summary>
    /// Auto-runs all EditMode tests when Unity compiles and writes results to
    /// %TEMP%\unity-parksmart-test-results.txt
    /// Trigger manually: ParkingSim → Run All EditMode Tests
    /// </summary>
    public static class AutoTestRunner
    {
        private static readonly string ResultsFile =
            Path.Combine(Path.GetTempPath(), "unity-parksmart-test-results.txt");

        [MenuItem("ParkingSim/Run All EditMode Tests")]
        public static void RunEditModeTests()
        {
            Debug.Log("[AutoTestRunner] Starting EditMode tests...");

            var api = ScriptableObject.CreateInstance<TestRunnerApi>();

            var callbacks = new TestCallbacks();
            api.RegisterCallbacks(callbacks);

            var filter = new Filter { testMode = TestMode.EditMode };
            api.Execute(new ExecutionSettings(filter));
        }

        private class TestCallbacks : ICallbacks
        {
            private readonly List<string> passed  = new();
            private readonly List<string> failed  = new();
            private readonly List<string> skipped = new();
            private int total;

            public void RunStarted(ITestAdaptor testsToRun) { }

            public void RunFinished(ITestResultAdaptor result)
            {
                WriteResults();
            }

            public void TestStarted(ITestAdaptor test)
            {
                if (test.IsSuite) return;
                total++;
            }

            public void TestFinished(ITestResultAdaptor result)
            {
                if (result.Test.IsSuite) return;

                string name = result.Test.FullName;
                switch (result.TestStatus)
                {
                    case UnityEditor.TestTools.TestRunner.Api.TestStatus.Passed:
                        passed.Add(name);
                        break;
                    case UnityEditor.TestTools.TestRunner.Api.TestStatus.Failed:
                        string msg = result.Message ?? "";
                        failed.Add($"{name}\n    {msg}");
                        break;
                    default:
                        skipped.Add(name);
                        break;
                }
            }

            private void WriteResults()
            {
                var sb = new System.Text.StringBuilder();
                sb.AppendLine("=== ParkSmart Unity Test Results ===");
                sb.AppendLine($"Time: {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
                sb.AppendLine($"Total: {total}  Passed: {passed.Count}  Failed: {failed.Count}  Skipped: {skipped.Count}");
                sb.AppendLine();

                if (failed.Count > 0)
                {
                    sb.AppendLine("--- FAILED ---");
                    foreach (var f in failed) sb.AppendLine($"  FAIL: {f}");
                    sb.AppendLine();
                }

                sb.AppendLine("--- PASSED ---");
                foreach (var p in passed) sb.AppendLine($"  PASS: {p}");

                if (skipped.Count > 0)
                {
                    sb.AppendLine();
                    sb.AppendLine("--- SKIPPED ---");
                    foreach (var s in skipped) sb.AppendLine($"  SKIP: {s}");
                }

                File.WriteAllText(ResultsFile, sb.ToString());
                Debug.Log($"[AutoTestRunner] Results written to: {ResultsFile}");
                Debug.Log($"[AutoTestRunner] Passed: {passed.Count} / Failed: {failed.Count} / Total: {total}");

                if (failed.Count > 0)
                {
                    Debug.LogError($"[AutoTestRunner] {failed.Count} test(s) FAILED!");
                    foreach (var f in failed)
                        Debug.LogError($"  FAIL: {f}");
                }
                else
                {
                    Debug.Log($"[AutoTestRunner] All {passed.Count} tests PASSED!");
                }
            }
        }
    }
}
