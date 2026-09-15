// Copyright:
//   - Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier:
//   - MIT
// Confidential:
//   - false
// License-File:
//   - LICENSE-MIT
//
// Boundary-Contract:
// - Owns:
//   - A small turn-based Snake game for classic-budget guest C.
// - Must-Not:
//   - Use libc, heap allocation, clocks, terminal APIs, files, or a hosted ABI.
// - Allows:
//   - Inputs: classic Malbolge input words through one compiler intrinsic.
//   - Outputs: ASCII and ANSI bytes through one compiler intrinsic.
//   - Side effects: fundamental guest byte input and output only.
// - Split-When:
//   - Split when another game needs independent state or interaction policy.
// - Merge-When:
//   - Merge when another fixture owns the same complete game loop.
// - Summary:
//   - Provide a self-contained playable Linux terminal guest-C fixture.
// - Description:
//   - Uses a 12 by 8 board, bounded snake storage, deterministic food,
//     collision
//     checks, score rendering, and turn-based WASD input.
// - Usage:
//   - Run in a Linux ANSI terminal; canonical input intentionally uses Enter.
// - Defaults:
//   - Start moving right with a three-cell snake and one deterministic food.
//

//! Self-contained turn-based Snake for Linux classic-budget testing.

unsigned int __malbolge_input_word(void);
void __malbolge_output_byte(unsigned int value);

enum
{
    BOARD_HEIGHT = 8,
    BOARD_WIDTH = 12,
    CLASSIC_EOF_WORD = 59048,
    CLASSIC_MODULUS = 59049,
    DIRECTION_DOWN = 1,
    DIRECTION_LEFT = 2,
    DIRECTION_RIGHT = 0,
    DIRECTION_UP = 3,
    MAX_LENGTH = 24
};

typedef struct SnakeGame
{
    unsigned int snake_x[MAX_LENGTH];
    unsigned int snake_y[MAX_LENGTH];
    unsigned int length;
    unsigned int direction;
    unsigned int food_x;
    unsigned int food_y;
    unsigned int food_seed;
    unsigned int score;
    unsigned int game_over;
} SnakeGame;

static void emit_byte(unsigned int value)
{
    __malbolge_output_byte(value);
}

static void emit_text(const char *text)
{
    while (*text != '\0')
    {
        emit_byte((unsigned int)(unsigned char)*text);
        ++text;
    }
}

static void emit_unsigned(unsigned int value)
{
    unsigned int digits[10];
    unsigned int count = 0U;

    if (value == 0U)
    {
        emit_byte(48U);
        return;
    }

    while (value != 0U)
    {
        digits[count] = value % 10U;
        value /= 10U;
        ++count;
    }
    while (count != 0U)
    {
        --count;
        emit_byte(48U + digits[count]);
    }
}

static void clear_terminal(void)
{
    emit_byte(27U);
    emit_byte(91U);
    emit_byte(50U);
    emit_byte(74U);
}

static void home_terminal(void)
{
    emit_byte(27U);
    emit_byte(91U);
    emit_byte(72U);
}

static unsigned int cell_is_snake(const SnakeGame *game, unsigned int x,
                                  unsigned int y, unsigned int limit)
{
    unsigned int index = 0U;

    while (index < limit)
    {
        if (game->snake_x[index] == x && game->snake_y[index] == y)
        {
            return 1U;
        }
        ++index;
    }
    return 0U;
}

static void place_food(SnakeGame *game)
{
    unsigned int attempts = 0U;

    while (attempts < BOARD_WIDTH * BOARD_HEIGHT)
    {
        unsigned int cell;

        game->food_seed =
            (game->food_seed * 17U + 11U) % CLASSIC_MODULUS;
        cell = game->food_seed % (BOARD_WIDTH * BOARD_HEIGHT);
        game->food_x = cell % BOARD_WIDTH;
        game->food_y = cell / BOARD_WIDTH;
        if (cell_is_snake(game, game->food_x, game->food_y, game->length) ==
            0U)
        {
            return;
        }
        ++attempts;
    }

    game->game_over = 1U;
}

static void initialize_game(SnakeGame *game)
{
    game->snake_x[0] = 6U;
    game->snake_y[0] = 4U;
    game->snake_x[1] = 5U;
    game->snake_y[1] = 4U;
    game->snake_x[2] = 4U;
    game->snake_y[2] = 4U;
    game->length = 3U;
    game->direction = DIRECTION_RIGHT;
    game->food_x = 9U;
    game->food_y = 4U;
    game->food_seed = 17U;
    game->score = 0U;
    game->game_over = 0U;
}

static unsigned int render_cell(const SnakeGame *game, unsigned int x,
                                unsigned int y)
{
    if (game->snake_x[0] == x && game->snake_y[0] == y)
    {
        return 64U;
    }
    if (cell_is_snake(game, x, y, game->length) != 0U)
    {
        return 111U;
    }
    if (game->food_x == x && game->food_y == y)
    {
        return 42U;
    }
    return 32U;
}

static void render_game(const SnakeGame *game)
{
    unsigned int y = 0U;

    home_terminal();
    emit_text("Malbolge Snake - Linux / classic budget\n");
    emit_text("+------------+\n");
    while (y < BOARD_HEIGHT)
    {
        unsigned int x = 0U;

        emit_byte(124U);
        while (x < BOARD_WIDTH)
        {
            emit_byte(render_cell(game, x, y));
            ++x;
        }
        emit_byte(124U);
        emit_byte(10U);
        ++y;
    }
    emit_text("+------------+\nScore: ");
    emit_unsigned(game->score);
    emit_text("  WASD + Enter, q quits\n");
    if (game->game_over != 0U)
    {
        emit_text("Game over\n");
    }
}

static unsigned int direction_is_opposite(unsigned int current,
                                          unsigned int candidate)
{
    return (current == DIRECTION_RIGHT && candidate == DIRECTION_LEFT) ||
        (current == DIRECTION_LEFT && candidate == DIRECTION_RIGHT) ||
        (current == DIRECTION_UP && candidate == DIRECTION_DOWN) ||
        (current == DIRECTION_DOWN && candidate == DIRECTION_UP);
}

static unsigned int update_direction(SnakeGame *game, unsigned int input)
{
    unsigned int candidate;

    if (input == 119U || input == 87U)
    {
        candidate = DIRECTION_UP;
    }
    else if (input == 115U || input == 83U)
    {
        candidate = DIRECTION_DOWN;
    }
    else if (input == 97U || input == 65U)
    {
        candidate = DIRECTION_LEFT;
    }
    else if (input == 100U || input == 68U)
    {
        candidate = DIRECTION_RIGHT;
    }
    else
    {
        return 0U;
    }

    if (game->length > 1U &&
        direction_is_opposite(game->direction, candidate) != 0U)
    {
        return 0U;
    }
    game->direction = candidate;
    return 1U;
}

static void step_game(SnakeGame *game)
{
    unsigned int next_x = game->snake_x[0];
    unsigned int next_y = game->snake_y[0];
    unsigned int growing;
    unsigned int collision_limit;
    unsigned int index;

    if (game->direction == DIRECTION_RIGHT)
    {
        if (next_x + 1U >= BOARD_WIDTH)
        {
            game->game_over = 1U;
            return;
        }
        ++next_x;
    }
    else if (game->direction == DIRECTION_DOWN)
    {
        if (next_y + 1U >= BOARD_HEIGHT)
        {
            game->game_over = 1U;
            return;
        }
        ++next_y;
    }
    else if (game->direction == DIRECTION_LEFT)
    {
        if (next_x == 0U)
        {
            game->game_over = 1U;
            return;
        }
        --next_x;
    }
    else
    {
        if (next_y == 0U)
        {
            game->game_over = 1U;
            return;
        }
        --next_y;
    }

    growing = next_x == game->food_x && next_y == game->food_y;
    collision_limit = game->length;
    if (growing == 0U && collision_limit != 0U)
    {
        --collision_limit;
    }
    if (cell_is_snake(game, next_x, next_y, collision_limit) != 0U)
    {
        game->game_over = 1U;
        return;
    }

    if (growing != 0U)
    {
        if (game->length == MAX_LENGTH)
        {
            game->game_over = 1U;
            return;
        }
        ++game->length;
        ++game->score;
    }

    index = game->length;
    while (index > 1U)
    {
        --index;
        game->snake_x[index] = game->snake_x[index - 1U];
        game->snake_y[index] = game->snake_y[index - 1U];
    }
    game->snake_x[0] = next_x;
    game->snake_y[0] = next_y;

    if (growing != 0U)
    {
        place_food(game);
    }
}

static void emit_goodbye(const SnakeGame *game)
{
    emit_text("Bye. Score: ");
    emit_unsigned(game->score);
    emit_text(" Length: ");
    emit_unsigned(game->length);
    emit_byte(10U);
}

int main(void)
{
    SnakeGame game;

    initialize_game(&game);
    clear_terminal();
    render_game(&game);

    while (game.game_over == 0U)
    {
        const unsigned int input = __malbolge_input_word();

        if (input == CLASSIC_EOF_WORD || input == 113U || input == 81U)
        {
            emit_goodbye(&game);
            return 0;
        }
        if (update_direction(&game, input) == 0U)
        {
            continue;
        }
        step_game(&game);
        render_game(&game);
    }

    emit_goodbye(&game);
    return 0;
}
