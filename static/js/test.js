/**
 * Quiz Platform - Test Page JavaScript
 * Handles timer, tab switching detection, and test submission
 */

// ===== Global Variables =====
let timeRemaining = TEST_DURATION; // in seconds
let timerInterval = null;
let tabSwitchCount = 0;
const MAX_TAB_SWITCHES = 3;
let testSubmitted = false;
let answers = {};

// ===== Timer Functions =====

/**
 * Format seconds into MM:SS format
 */
function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

/**
 * Update timer display
 */
function updateTimerDisplay() {
  const timerElement = document.getElementById("timer");
  timerElement.textContent = formatTime(timeRemaining);

  // Add warning class when time is running low (less than 5 minutes)
  if (timeRemaining <= 300 && timeRemaining > 0) {
    timerElement.classList.add("timer-warning");
  }
}

/**
 * Start the countdown timer
 */
function startTimer() {
  updateTimerDisplay();

  timerInterval = setInterval(() => {
    timeRemaining--;
    updateTimerDisplay();

    // Auto-submit when time is up
    if (timeRemaining <= 0) {
      clearInterval(timerInterval);
      autoSubmitTest("timeout");
    }
  }, 1000);
}

// ===== Tab Switching Detection =====

/**
 * Handle visibility change (tab switching)
 */
function handleVisibilityChange() {
  if (document.hidden && !testSubmitted) {
    tabSwitchCount++;
    logTabSwitch();

    // Update display
    updateTabSwitchDisplay();

    if (tabSwitchCount <= MAX_TAB_SWITCHES) {
      showTabWarningModal();
    }

    if (tabSwitchCount > MAX_TAB_SWITCHES) {
      autoSubmitTest("tab_violation");
    }
  }
}

/**
 * Log tab switch to server
 */
function logTabSwitch() {
  fetch("/api/log_tab_switch", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({}),
  }).catch((error) => {
    console.error("Error logging tab switch:", error);
  });
}

/**
 * Update tab switch display counter
 */
function updateTabSwitchDisplay() {
  const displayElement = document.getElementById("tabSwitchDisplay");
  displayElement.textContent = `${tabSwitchCount} / ${MAX_TAB_SWITCHES}`;

  // Change color based on count
  if (tabSwitchCount >= MAX_TAB_SWITCHES) {
    displayElement.style.color = "#EF4444"; // Red
  } else if (tabSwitchCount >= 2) {
    displayElement.style.color = "#F59E0B"; // Orange
  }
}

/**
 * Show tab switch warning modal
 */
function showTabWarningModal() {
  const modal = document.getElementById("tabWarningModal");
  const switchCountSpan = document.getElementById("switchCount");

  switchCountSpan.textContent = tabSwitchCount;
  modal.classList.add("active");

  // Play warning sound (optional)
  playWarningSound();
}

/**
 * Close warning modal
 */
function closeWarningModal() {
  const modal = document.getElementById("tabWarningModal");
  modal.classList.remove("active");
}

/**
 * Show test terminated modal
 */
function showTestTerminatedModal() {
  const modal = document.getElementById("testTerminatedModal");
  modal.classList.add("active");
}

/**
 * Play warning sound (simple beep using Web Audio API)
 */
function playWarningSound() {
  try {
    const audioContext = new (
      window.AudioContext || window.webkitAudioContext
    )();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = 800;
    oscillator.type = "sine";

    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(
      0.01,
      audioContext.currentTime + 0.5,
    );

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.5);
  } catch (error) {
    console.error("Audio not supported:", error);
  }
}

// ===== Answer Collection =====

/**
 * Collect all answers from form
 */
function collectAnswers() {
  const answers = {};
  const radioButtons = document.querySelectorAll(".option-input:checked");

  radioButtons.forEach((radio) => {
    const questionId = radio.dataset.questionId;
    const answerValue = radio.value;
    answers[questionId] = answerValue;
  });

  return answers;
}

/**
 * Check if all questions are answered
 */
function areAllQuestionsAnswered() {
  const totalQuestions = TOTAL_QUESTIONS;
  const answeredQuestions = document.querySelectorAll(
    ".option-input:checked",
  ).length;
  return answeredQuestions === totalQuestions;
}

// ===== Test Submission =====

/**
 * Confirm before manual submission
 */
function confirmSubmit() {
  if (testSubmitted) return;

  const answeredCount = document.querySelectorAll(
    ".option-input:checked",
  ).length;
  const unansweredCount = TOTAL_QUESTIONS - answeredCount;

  let message = "Are you sure you want to submit your test?";

  if (unansweredCount > 0) {
    message += `\n\nYou have ${unansweredCount} unanswered question(s).`;
  }

  if (confirm(message)) {
    submitTest("manual");
  }
}

/**
 * Auto-submit test (timeout or tab violation)
 */
function autoSubmitTest(reason) {
  if (testSubmitted) return;

  if (reason === "tab_violation") {
    showTestTerminatedModal();
    setTimeout(() => {
      submitTest(reason);
    }, 2000);
  } else {
    submitTest(reason);
  }
}

/**
 * Submit test to server
 */
function submitTest(submissionType) {
  if (testSubmitted) return;

  testSubmitted = true;

  // Stop timer
  if (timerInterval) {
    clearInterval(timerInterval);
  }

  // Collect answers
  const answers = collectAnswers();

  // Prepare data
  const data = {
    answers: answers,
    tab_switches: tabSwitchCount,
    submission_type: submissionType,
  };

  // Show loading state
  const submitButton = document.querySelector(".submit-section .btn");
  if (submitButton) {
    submitButton.disabled = true;
    submitButton.innerHTML = "<span>Submitting...</span>";
  }

  // Send to server
  fetch("/api/submit_test", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        // Redirect to score page
        window.location.href = "/score";
      } else {
        alert("Error submitting test. Please try again.");
        testSubmitted = false;
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.innerHTML = "Submit Test";
        }
      }
    })
    .catch((error) => {
      console.error("Error submitting test:", error);
      alert("Error submitting test. Please try again.");
      testSubmitted = false;
      if (submitButton) {
        submitButton.disabled = false;
        submitButton.innerHTML = "Submit Test";
      }
    });
}

// ===== Event Listeners =====

/**
 * Track answer selections
 */
function setupAnswerTracking() {
  const radioButtons = document.querySelectorAll(".option-input");
  radioButtons.forEach((radio) => {
    radio.addEventListener("change", function () {
      const questionId = this.dataset.questionId;
      const answerValue = this.value;
      answers[questionId] = answerValue;

      // Visual feedback
      const questionCard = document.getElementById(`question-${questionId}`);
      if (questionCard) {
        questionCard.style.borderLeft = "4px solid var(--primary-blue)";
      }
    });
  });
}

/**
 * Prevent accidental page refresh
 */
function preventAccidentalRefresh(e) {
  if (!testSubmitted) {
    e.preventDefault();
    e.returnValue = "";
    return "";
  }
}

/**
 * Prevent right-click context menu (optional security measure)
 */
function preventContextMenu(e) {
  e.preventDefault();
  return false;
}

/**
 * Prevent text selection (optional security measure)
 */
function preventTextSelection() {
  document.body.style.userSelect = "none";
  document.body.style.webkitUserSelect = "none";
  document.body.style.mozUserSelect = "none";
  document.body.style.msUserSelect = "none";
}

// ===== Keyboard Shortcuts =====

/**
 * Handle keyboard shortcuts
 */
function handleKeyboardShortcuts(e) {
  // Prevent certain key combinations
  if (e.ctrlKey || e.metaKey) {
    // Prevent Ctrl+P (Print)
    if (e.key === "p" || e.keyCode === 80) {
      e.preventDefault();
      return false;
    }
    // Prevent Ctrl+S (Save)
    if (e.key === "s" || e.keyCode === 83) {
      e.preventDefault();
      return false;
    }
    // Prevent Ctrl+U (View Source)
    if (e.key === "u" || e.keyCode === 85) {
      e.preventDefault();
      return false;
    }
  }

  // Prevent F12 (Developer Tools)
  if (e.keyCode === 123) {
    e.preventDefault();
    return false;
  }
}

// ===== Initialization =====

/**
 * Initialize the test page
 */
function initializeTestPage() {
  console.log("Initializing test page...");

  // Start timer
  startTimer();

  // Setup tab switching detection
  document.addEventListener("visibilitychange", handleVisibilityChange);

  // Setup answer tracking
  setupAnswerTracking();

  // Prevent accidental page refresh
  window.addEventListener("beforeunload", preventAccidentalRefresh);

  // Optional security measures (uncomment if needed)
  // document.addEventListener('contextmenu', preventContextMenu);
  // preventTextSelection();
  // document.addEventListener('keydown', handleKeyboardShortcuts);

  // Focus on first question
  const firstQuestion = document.querySelector(".question-card");
  if (firstQuestion) {
    firstQuestion.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  console.log("Test page initialized successfully");
}

// ===== Auto-save (Optional Enhancement) =====

/**
 * Auto-save answers periodically
 */
function setupAutoSave() {
  setInterval(() => {
    if (!testSubmitted) {
      const currentAnswers = collectAnswers();
      // Could save to localStorage or send to server
      localStorage.setItem(
        "quiz_answers_backup",
        JSON.stringify(currentAnswers),
      );
    }
  }, 30000); // Save every 30 seconds
}

// ===== Start Everything =====

// Wait for DOM to be ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeTestPage);
} else {
  initializeTestPage();
}

// Optional: Setup auto-save
// setupAutoSave();

// ===== Utility Functions =====

/**
 * Scroll to unanswered question
 */
function scrollToFirstUnanswered() {
  const allQuestions = document.querySelectorAll(".question-card");

  for (let i = 0; i < allQuestions.length; i++) {
    const questionCard = allQuestions[i];
    const questionId = questionCard.id.replace("question-", "");
    const isAnswered = document.querySelector(
      `input[data-question-id="${questionId}"]:checked`,
    );

    if (!isAnswered) {
      questionCard.scrollIntoView({ behavior: "smooth", block: "center" });
      questionCard.style.animation = "pulse 1s ease-in-out";
      setTimeout(() => {
        questionCard.style.animation = "";
      }, 1000);
      break;
    }
  }
}

/**
 * Get test progress percentage
 */
function getProgress() {
  const answeredCount = Object.keys(answers).length;
  return Math.round((answeredCount / TOTAL_QUESTIONS) * 100);
}

/**
 * Log test activity (for debugging)
 */
function logActivity(action, details = {}) {
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${action}:`, details);
}

// Export functions for potential external use
window.testFunctions = {
  confirmSubmit,
  closeWarningModal,
  scrollToFirstUnanswered,
  getProgress,
};
