(function () {
  var DIRECTIONS = {
    up: { x: 0, y: -1 },
    down: { x: 0, y: 1 },
    left: { x: -1, y: 0 },
    right: { x: 1, y: 0 }
  };

  function cloneSegment(segment) {
    return { x: segment.x, y: segment.y };
  }

  function areOpposites(current, next) {
    return current.x + next.x === 0 && current.y + next.y === 0;
  }

  function getDirectionVector(directionName) {
    return DIRECTIONS[directionName];
  }

  function createFood(snake, width, height, rng) {
    var openCells = [];
    var occupied = new Set();

    snake.forEach(function (segment) {
      occupied.add(segment.x + "," + segment.y);
    });

    for (var y = 0; y < height; y += 1) {
      for (var x = 0; x < width; x += 1) {
        var key = x + "," + y;
        if (!occupied.has(key)) {
          openCells.push({ x: x, y: y });
        }
      }
    }

    if (openCells.length === 0) {
      return null;
    }

    var index = Math.floor(rng() * openCells.length);
    return openCells[index];
  }

  function createInitialState(options, rng) {
    var width = options && options.width ? options.width : 16;
    var height = options && options.height ? options.height : 16;
    var startX = Math.floor(width / 2);
    var startY = Math.floor(height / 2);
    var snake = [
      { x: startX, y: startY },
      { x: startX - 1, y: startY },
      { x: startX - 2, y: startY }
    ];

    return {
      width: width,
      height: height,
      snake: snake,
      direction: "right",
      nextDirection: "right",
      food: createFood(snake, width, height, rng || Math.random),
      score: 0,
      status: "ready"
    };
  }

  function queueDirection(state, nextDirection) {
    if (!DIRECTIONS[nextDirection]) {
      return state;
    }

    var currentVector = getDirectionVector(state.direction);
    var nextVector = getDirectionVector(nextDirection);

    if (areOpposites(currentVector, nextVector)) {
      return state;
    }

    return Object.assign({}, state, {
      nextDirection: nextDirection
    });
  }

  function stepGame(state, rng) {
    if (state.status !== "running") {
      return state;
    }

    var direction = state.nextDirection;
    var vector = getDirectionVector(direction);
    var head = state.snake[0];
    var nextHead = {
      x: head.x + vector.x,
      y: head.y + vector.y
    };
    var willEat = state.food && nextHead.x === state.food.x && nextHead.y === state.food.y;
    var nextSnake = [nextHead].concat(
      state.snake.slice(0, willEat ? state.snake.length : state.snake.length - 1).map(cloneSegment)
    );

    if (isOutOfBounds(nextHead, state.width, state.height) || hitsSelf(nextHead, nextSnake.slice(1))) {
      return Object.assign({}, state, {
        direction: direction,
        nextDirection: direction,
        snake: nextSnake,
        status: "gameover"
      });
    }

    var nextFood = state.food;
    var nextScore = state.score;

    if (willEat) {
      nextScore += 1;
      nextFood = createFood(nextSnake, state.width, state.height, rng || Math.random);
    }

    return Object.assign({}, state, {
      direction: direction,
      nextDirection: direction,
      snake: nextSnake,
      food: nextFood,
      score: nextScore
    });
  }

  function isOutOfBounds(position, width, height) {
    return position.x < 0 || position.y < 0 || position.x >= width || position.y >= height;
  }

  function hitsSelf(head, body) {
    return body.some(function (segment) {
      return segment.x === head.x && segment.y === head.y;
    });
  }

  window.SnakeLogic = {
    DIRECTIONS: DIRECTIONS,
    createFood: createFood,
    createInitialState: createInitialState,
    queueDirection: queueDirection,
    stepGame: stepGame,
    isOutOfBounds: isOutOfBounds,
    hitsSelf: hitsSelf
  };
}());