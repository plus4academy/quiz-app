/**
 * Quiz Platform - Test Page JavaScript (Paginated Version)
 * One question per page with navigation palette
 */

// ===== Global Variables =====
let timeRemaining = TEST_DURATION;
let timerInterval = null;
let tabSwitchCount = 0;
const MAX_TAB_SWITCHES = 3;
let testSubmitted = false;
let testStarted = false;

// Question state tracking
let currentQuestionIndex = 0;
let answers = {}; // {questionId: answerIndex}
let visitedQuestions = new Set(); // Track visited questions
let markedForReview = new Set(); // Track marked questions

// ===== Timer Functions =====
function formatTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

function updateTimerDisplay() {
  const timerElement = document.getElementById("timer");
  timerElement.textContent = formatTime(timeRemaining);

  if (timeRemaining <= 300 && timeRemaining > 0) {
    timerElement.classList.add("timer-warning");
  }
}

function startTimer() {
  updateTimerDisplay();
  timerInterval = setInterval(() => {
    timeRemaining--;
    updateTimerDisplay();

    if (timeRemaining <= 0) {
      clearInterval(timerInterval);
      autoSubmitTest("timeout");
    }
  }, 1000);
}

// ===== Question Navigation =====
function startTest() {
  document.getElementById("instructionsPanel").style.display = "none";
  document.getElementById("questionContainer").style.display = "block";
  testStarted = true;
  initializeQuestionPalette();
  showQuestion(0);
  startTimer();
}

function showQuestion(index) {
  if (index < 0 || index >= questions.length) return;

  currentQuestionIndex = index;
  visitedQuestions.add(index);

  const question = questions[index];
  const container = document.getElementById("currentQuestion");

  // Update question number
  document.getElementById("questionNumber").textContent =
    `Question ${index + 1}`;

  // Render question
  container.innerHTML = `
    <div class="question-text-large">${question.question}</div>
    <div class="options-container-large">
      ${question.options
        .map(
          (option, optIdx) => `
        <label class="option-label-large ${answers[question.id] == optIdx ? "selected" : ""}">
          <input 
            type="radio" 
            name="question_${question.id}" 
            value="${optIdx}" 
            class="option-input-large"
            ${answers[question.id] == optIdx ? "checked" : ""}
            onchange="selectAnswer(${question.id}, ${optIdx})"
          >
          <span class="option-content">
            <span class="option-letter-large">${["A", "B", "C", "D"][optIdx]}</span>
            <span class="option-text-large">${option}</span>
          </span>
          <span class="option-checkmark">✓</span>
        </label>
      `,
        )
        .join("")}
    </div>
  `;

  // Update navigation buttons
  document.getElementById("prevBtn").disabled = index === 0;

  const nextBtn = document.getElementById("nextBtn");
  const submitBtn = document.getElementById("submitBtn");

  if (index === questions.length - 1) {
    nextBtn.style.display = "none";
    submitBtn.style.display = "inline-flex";
  } else {
    nextBtn.style.display = "inline-flex";
    submitBtn.style.display = "none";
  }

  // Update mark for review button
  const markBtn = document.getElementById("markReviewBtn");
  if (markedForReview.has(index)) {
    markBtn.classList.add("marked");
    markBtn.innerHTML = `
      <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
      </svg>
      Marked
    `;
  } else {
    markBtn.classList.remove("marked");
    markBtn.innerHTML = `
      <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
        <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
      </svg>
      Mark for Review
    `;
  }

  updateQuestionPalette();
}

function nextQuestion() {
  if (currentQuestionIndex < questions.length - 1) {
    showQuestion(currentQuestionIndex + 1);
  }
}

function previousQuestion() {
  if (currentQuestionIndex > 0) {
    showQuestion(currentQuestionIndex - 1);
  }
}

function jumpToQuestion(index) {
  showQuestion(index);
  if (window.innerWidth <= 1024) {
    toggleQuestionPalette(); // Close palette on mobile after selection
  }
}

function selectAnswer(questionId, answerIndex) {
  answers[questionId] = answerIndex;
  updateQuestionPalette();

  // Add visual feedback
  document.querySelectorAll(".option-label-large").forEach((label) => {
    label.classList.remove("selected");
  });
  event.target.closest(".option-label-large").classList.add("selected");
}

function markForReview() {
  if (markedForReview.has(currentQuestionIndex)) {
    markedForReview.delete(currentQuestionIndex);
  } else {
    markedForReview.add(currentQuestionIndex);
  }
  showQuestion(currentQuestionIndex); // Refresh to update button
}

// ===== Question Palette =====
function initializeQuestionPalette() {
  const grid = document.getElementById("paletteGrid");
  grid.innerHTML = questions
    .map(
      (q, idx) => `
    <button 
      class="palette-btn" 
      id="paletteBtn${idx}"
      onclick="jumpToQuestion(${idx})"
      title="Question ${idx + 1}"
    >
      ${idx + 1}
    </button>
  `,
    )
    .join("");
  updateQuestionPalette();
}

function updateQuestionPalette() {
  let answeredCount = 0;
  let notAnsweredButVisited = 0;
  let notVisitedCount = 0;

  questions.forEach((q, idx) => {
    const btn = document.getElementById(`paletteBtn${idx}`);
    if (!btn) return;

    // Remove all status classes
    btn.classList.remove("answered", "visited", "current", "marked");

    // Add current class
    if (idx === currentQuestionIndex) {
      btn.classList.add("current");
    }

    // Add marked class
    if (markedForReview.has(idx)) {
      btn.classList.add("marked");
    }

    // Add answered/visited class
    if (answers[q.id] !== undefined) {
      btn.classList.add("answered");
      answeredCount++;
    } else if (visitedQuestions.has(idx)) {
      btn.classList.add("visited");
      notAnsweredButVisited++;
    } else {
      notVisitedCount++;
    }
  });

  // Update stats
  document.getElementById("answeredCount").textContent = answeredCount;
  document.getElementById("notAnsweredCount").textContent =
    notAnsweredButVisited;
  document.getElementById("notVisitedCount").textContent = notVisitedCount;
}

function toggleQuestionPalette() {
  const palette = document.getElementById("questionPalette");
  palette.classList.toggle("active");
}

// ===== Tab Switching Detection =====
function handleVisibilityChange() {
  if (document.hidden && !testSubmitted && testStarted) {
    tabSwitchCount++;
    logTabSwitch();
    updateTabSwitchDisplay();

    if (tabSwitchCount <= MAX_TAB_SWITCHES) {
      showTabWarningModal();
    }

    if (tabSwitchCount > MAX_TAB_SWITCHES) {
      autoSubmitTest("tab_violation");
    }
  }
}

function logTabSwitch() {
  fetch("/api/log_tab_switch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  }).catch((err) => console.error("Error logging tab switch:", err));
}

function updateTabSwitchDisplay() {
  const displayElement = document.getElementById("tabSwitchDisplay");
  displayElement.textContent = `${tabSwitchCount} / ${MAX_TAB_SWITCHES}`;

  if (tabSwitchCount >= MAX_TAB_SWITCHES) {
    displayElement.style.color = "#EF4444";
  } else if (tabSwitchCount >= 2) {
    displayElement.style.color = "#F59E0B";
  }
}

function showTabWarningModal() {
  const modal = document.getElementById("tabWarningModal");
  const switchCountSpan = document.getElementById("switchCount");
  switchCountSpan.textContent = tabSwitchCount;
  modal.classList.add("active");
  playWarningSound();
}

function closeWarningModal() {
  document.getElementById("tabWarningModal").classList.remove("active");
}

function showTestTerminatedModal() {
  document.getElementById("testTerminatedModal").classList.add("active");
}

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

// ===== Test Submission =====
function confirmSubmit() {
  if (testSubmitted) return;

  const answeredCount = Object.keys(answers).length;
  const unansweredCount = TOTAL_QUESTIONS - answeredCount;

  let message = "Are you sure you want to submit your test?";
  if (unansweredCount > 0) {
    message += `\n\nYou have ${unansweredCount} unanswered question(s).`;
  }
  if (markedForReview.size > 0) {
    message += `\n\n${markedForReview.size} question(s) marked for review.`;
  }

  if (confirm(message)) {
    submitTest("manual");
  }
}

function autoSubmitTest(reason) {
  if (testSubmitted) return;

  if (reason === "tab_violation") {
    showTestTerminatedModal();
    setTimeout(() => submitTest(reason), 2000);
  } else {
    submitTest(reason);
  }
}

function submitTest(submissionType) {
  if (testSubmitted) return;
  testSubmitted = true;

  if (timerInterval) clearInterval(timerInterval);

  const data = {
    answers: answers,
    tab_switches: tabSwitchCount,
    submission_type: submissionType,
  };

  const submitBtn = document.getElementById("submitBtn");
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = "<span>Submitting...</span>";
  }

  fetch("/api/submit_test", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        window.location.href = "/score";
      } else {
        alert("Error submitting test. Please try again.");
        testSubmitted = false;
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.innerHTML = "Submit Test";
        }
      }
    })
    .catch((error) => {
      console.error("Error submitting test:", error);
      alert("Error submitting test. Please try again.");
      testSubmitted = false;
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "Submit Test";
      }
    });
}

// ===== Event Listeners =====
function preventAccidentalRefresh(e) {
  if (!testSubmitted && testStarted) {
    e.preventDefault();
    e.returnValue = "";
    return "";
  }
}

// ===== Keyboard Shortcuts =====
document.addEventListener("keydown", (e) => {
  if (!testStarted || testSubmitted) return;

  // Arrow keys for navigation
  if (e.key === "ArrowRight" && currentQuestionIndex < questions.length - 1) {
    e.preventDefault();
    nextQuestion();
  } else if (e.key === "ArrowLeft" && currentQuestionIndex > 0) {
    e.preventDefault();
    previousQuestion();
  }

  // Number keys (1-4) for selecting options
  if (e.key >= "1" && e.key <= "4") {
    const optionIndex = parseInt(e.key) - 1;
    const question = questions[currentQuestionIndex];
    if (optionIndex < question.options.length) {
      e.preventDefault();
      selectAnswer(question.id, optionIndex);
      // Trigger the radio button
      const radio = document.querySelector(
        `input[name="question_${question.id}"][value="${optionIndex}"]`,
      );
      if (radio) radio.checked = true;
      showQuestion(currentQuestionIndex); // Refresh
    }
  }

  // M key for mark/unmark
  if (e.key === "m" || e.key === "M") {
    e.preventDefault();
    markForReview();
  }
});

// ===== Initialization =====
function initializeTestPage() {
  console.log("Initializing test page...");

  document.addEventListener("visibilitychange", handleVisibilityChange);
  window.addEventListener("beforeunload", preventAccidentalRefresh);

  // Close palette when clicking outside on mobile
  document.addEventListener("click", (e) => {
    const palette = document.getElementById("questionPalette");
    const toggleBtn = document.getElementById("paletteToggleBtn");
    if (
      window.innerWidth <= 1024 &&
      palette.classList.contains("active") &&
      !palette.contains(e.target) &&
      !toggleBtn.contains(e.target)
    ) {
      toggleQuestionPalette();
    }
  });

  console.log("Test page initialized successfully");
}

// Start
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeTestPage);
} else {
  initializeTestPage();
}
