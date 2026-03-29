(function () {
  var BOARD_SIZE = 16;
  var TICK_MS = 140;
  var logic = window.SnakeLogic;

  var boardElement = document.getElementById("board");
  var scoreElement = document.getElementById("score");
  var statusElement = document.getElementById("status");
  var startButton = document.getElementById("start-button");
  var pauseButton = document.getElementById("pause-button");
  var restartButton = document.getElementById("restart-button");
  var directionButtons = document.querySelectorAll("[data-direction]");

  var state = logic.createInitialState({ width: BOARD_SIZE, height: BOARD_SIZE });
  var timerId = null;
  var cells = [];

  function buildBoard() {
    var fragment = document.createDocumentFragment();

    boardElement.innerHTML = "";
    boardElement.style.gridTemplateColumns = "repeat(" + state.width + ", var(--size))";
    boardElement.style.gridTemplateRows = "repeat(" + state.height + ", var(--size))";

    for (var y = 0; y < state.height; y += 1) {
      for (var x = 0; x < state.width; x += 1) {
        var cell = document.createElement("div");
        cell.className = "cell";
        cell.setAttribute("role", "gridcell");
        fragment.appendChild(cell);
      }
    }

    boardElement.appendChild(fragment);
    cells = Array.prototype.slice.call(boardElement.children);
  }

  function getCellIndex(x, y) {
    return y * state.width + x;
  }

  function render() {
    cells.forEach(function (cell) {
      cell.className = "cell";
    });

    state.snake.forEach(function (segment, index) {
      var cell = cells[getCellIndex(segment.x, segment.y)];
      if (!cell) {
        return;
      }

      cell.classList.add("cell--snake");
      if (index === 0) {
        cell.classList.add("cell--head");
      }
    });

    if (state.food) {
      var foodCell = cells[getCellIndex(state.food.x, state.food.y)];
      if (foodCell) {
        foodCell.classList.add("cell--food");
      }
    }

    scoreElement.textContent = String(state.score);
    statusElement.textContent = getStatusLabel();
    pauseButton.textContent = state.status === "paused" ? "Resume" : "Pause";
  }

  function getStatusLabel() {
    if (state.status === "ready") {
      return "Press Start to play.";
    }

    if (state.status === "paused") {
      return "Game paused.";
    }

    if (state.status === "gameover") {
      return "Game over. Press Restart to try again.";
    }

    return "Game in progress.";
  }

  function tick() {
    state = logic.stepGame(state);
    render();

    if (state.status === "gameover") {
      stopTimer();
    }
  }

  function startTimer() {
    if (timerId !== null) {
      return;
    }

    timerId = window.setInterval(tick, TICK_MS);
  }

  function stopTimer() {
    if (timerId === null) {
      return;
    }

    window.clearInterval(timerId);
    timerId = null;
  }

  function startGame() {
    if (state.status === "gameover") {
      restartGame();
      return;
    }

    if (state.status === "ready" || state.status === "paused") {
      state = Object.assign({}, state, { status: "running" });
      startTimer();
      render();
    }
  }

  function togglePause() {
    if (state.status === "running") {
      state = Object.assign({}, state, { status: "paused" });
      stopTimer();
      render();
      return;
    }

    if (state.status === "paused" || state.status === "ready") {
      startGame();
    }
  }

  function restartGame() {
    stopTimer();
    state = logic.createInitialState({ width: BOARD_SIZE, height: BOARD_SIZE });
    render();
  }

  function setDirection(direction) {
    if (state.status === "gameover") {
      return;
    }

    state = logic.queueDirection(state, direction);

    if (state.status === "ready") {
      state = Object.assign({}, state, { status: "running" });
      startTimer();
    }

    render();
  }

  function handleKeydown(event) {
    var keyMap = {
      ArrowUp: "up",
      ArrowDown: "down",
      ArrowLeft: "left",
      ArrowRight: "right",
      w: "up",
      W: "up",
      a: "left",
      A: "left",
      s: "down",
      S: "down",
      d: "right",
      D: "right"
    };

    if (event.code === "Space") {
      event.preventDefault();
      togglePause();
      return;
    }

    if (keyMap[event.key]) {
      event.preventDefault();
      setDirection(keyMap[event.key]);
    }
  }

  startButton.addEventListener("click", startGame);
  pauseButton.addEventListener("click", togglePause);
  restartButton.addEventListener("click", restartGame);
  document.addEventListener("keydown", handleKeydown);

  directionButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setDirection(button.getAttribute("data-direction"));
    });
  });

  buildBoard();
  render();
}());