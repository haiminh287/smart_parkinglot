using System.Collections;
using System.Reflection;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using ParkingSim.Parking;

namespace ParkingSim.Tests
{
    [TestFixture]
    public class BarrierControllerTests
    {
        private GameObject barrierGo;
        private GameObject armGo;
        private BarrierController barrier;

        [SetUp]
        public void SetUp()
        {
            barrierGo = new GameObject("TestBarrier");
            barrier = barrierGo.AddComponent<BarrierController>();

            // Create arm child and wire it via reflection (barrierArm is [SerializeField] private)
            armGo = new GameObject("BarrierArm");
            armGo.transform.SetParent(barrierGo.transform);
            armGo.transform.localEulerAngles = Vector3.zero;

            SetPrivateField("barrierArm", armGo.transform);

            // Set speed very high so animation completes quickly in tests
            SetPrivateField("speed", 1000f);
        }

        [TearDown]
        public void TearDown()
        {
            if (barrierGo != null)
                Object.DestroyImmediate(barrierGo);
        }

        [Test]
        public void should_start_closed()
        {
            // Assert — barrier starts closed by default
            Assert.IsFalse(barrier.IsOpen, "Barrier should start in closed state");
        }

        [UnityTest]
        public IEnumerator should_open_and_fire_event()
        {
            // Arrange
            bool eventFired = false;
            barrier.OnBarrierOpened += () => eventFired = true;

            // Let Start() run
            yield return null;

            // Act
            barrier.Open();

            // Assert — IsOpen should be true immediately after calling Open()
            Assert.IsTrue(barrier.IsOpen, "IsOpen should be true after Open()");

            // Wait for animation to complete and event to fire
            // With speed=1000, should complete in a few frames
            float timeout = 2f;
            float elapsed = 0f;
            while (!eventFired && elapsed < timeout)
            {
                yield return null;
                elapsed += Time.deltaTime;
            }

            Assert.IsTrue(eventFired, "OnBarrierOpened event should have fired");
        }

        [UnityTest]
        public IEnumerator should_close_after_open_then_close()
        {
            // Arrange
            bool openFired = false;
            bool closeFired = false;
            barrier.OnBarrierOpened += () => openFired = true;
            barrier.OnBarrierClosed += () => closeFired = true;

            yield return null; // Let Start() run

            // Act — Open
            barrier.Open();

            float timeout = 2f;
            float elapsed = 0f;
            while (!openFired && elapsed < timeout)
            {
                yield return null;
                elapsed += Time.deltaTime;
            }
            Assert.IsTrue(openFired, "Precondition: barrier opened");

            // Act — Close
            barrier.Close();
            Assert.IsFalse(barrier.IsOpen, "IsOpen should be false after Close()");

            elapsed = 0f;
            while (!closeFired && elapsed < timeout)
            {
                yield return null;
                elapsed += Time.deltaTime;
            }

            // Assert
            Assert.IsTrue(closeFired, "OnBarrierClosed event should have fired");
            Assert.IsFalse(barrier.IsOpen);
        }

        [UnityTest]
        public IEnumerator should_open_then_close_via_coroutine()
        {
            // Arrange
            bool closeFired = false;
            barrier.OnBarrierClosed += () => closeFired = true;

            yield return null; // Let Start() run

            // Act — use OpenThenClose with minimal delay
            SetPrivateField("speed", 10000f); // ultra-fast for coroutine test
            barrier.StartCoroutine(barrier.OpenThenClose(0.1f));

            // Wait for open + delay + close animation
            float timeout = 3f;
            float elapsed = 0f;
            while (!closeFired && elapsed < timeout)
            {
                yield return null;
                elapsed += Time.deltaTime;
            }

            // Assert
            Assert.IsTrue(closeFired, "Barrier should have closed after OpenThenClose");
            Assert.IsFalse(barrier.IsOpen);
        }

        [Test]
        public void should_expose_isEntry_flag()
        {
            // Arrange + Act
            barrier.isEntry = true;

            // Assert
            Assert.IsTrue(barrier.isEntry);

            barrier.isEntry = false;
            Assert.IsFalse(barrier.isEntry);
        }

        // ─── Helper ──────────────────────────────────────────

        private void SetPrivateField(string fieldName, object value)
        {
            var field = typeof(BarrierController).GetField(fieldName,
                BindingFlags.NonPublic | BindingFlags.Instance);
            Assert.IsNotNull(field, $"Field '{fieldName}' not found on BarrierController");
            field.SetValue(barrier, value);
        }
    }
}
