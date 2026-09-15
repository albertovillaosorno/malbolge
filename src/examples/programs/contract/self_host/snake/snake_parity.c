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
//   - Deterministic white-box parity vectors for the Snake guest program.
// - Must-Not:
//   - Depend on libc, terminal state, clocks, or host game logic.
// - Allows:
//   - Inputs: the checked-in Snake implementation through source inclusion.
//   - Outputs: one canonical parity transcript through guest byte output.
//   - Side effects: fundamental guest byte output only.
// - Split-When:
//   - Another game needs independent parity vectors.
// - Merge-When:
//   - Another fixture owns the same Snake state-transition oracle.
// - Summary:
//   - Make native-C and future Malbolge Snake runs byte-comparable.
// - Description:
//   - Checks initialization, movement, growth, collisions, food, and rendering.
// - Usage:
//   - Run as guest C now; compile this same harness to Malbolge for parity
//     later.
// - Defaults:
//   - Fail closed on the first mismatching deterministic vector.
//

//! Deterministic Snake parity vectors reusable after C-to-Malbolge lowering.

#define main snake_guest_main
#define __malbolge_input_word snake_captured_input
#define __malbolge_output_byte snake_captured_output
#include "snake_classic.c"
#undef __malbolge_output_byte
#undef __malbolge_input_word
#undef main

void __malbolge_output_byte(unsigned int value);

static unsigned int captured_count;
static unsigned int captured_mismatch;
static const char *captured_expected;

unsigned int snake_captured_input(void)
{
    return CLASSIC_EOF_WORD;
}

void snake_captured_output(unsigned int value)
{
    const unsigned int expected =
        (unsigned int)(unsigned char)captured_expected[captured_count];

    if (captured_expected[captured_count] == '\0' ||
        expected != (value & 255U))
    {
        captured_mismatch = 1U;
    }
    ++captured_count;
}

static void parity_text(const char *text)
{
    while (*text != '\0')
    {
        __malbolge_output_byte((unsigned int)(unsigned char)*text);
        ++text;
    }
}

static void parity_unsigned(unsigned int value)
{
    unsigned int digits[10];
    unsigned int count = 0U;

    if (value == 0U)
    {
        __malbolge_output_byte(48U);
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
        __malbolge_output_byte(48U + digits[count]);
    }
}

static int parity_fail(unsigned int identifier)
{
    parity_text("SNAKE-PARITY-v1\nFAIL ");
    parity_unsigned(identifier);
    __malbolge_output_byte(10U);
    return 1;
}

static unsigned int initial_state_is_exact(const SnakeGame *game)
{
    return game->length == 3U && game->direction == DIRECTION_RIGHT &&
        game->snake_x[0] == 6U && game->snake_y[0] == 4U &&
        game->snake_x[1] == 5U && game->snake_y[1] == 4U &&
        game->snake_x[2] == 4U && game->snake_y[2] == 4U &&
        game->food_x == 9U && game->food_y == 4U &&
        game->food_seed == 17U && game->score == 0U &&
        game->game_over == 0U;
}

static unsigned int test_initial_render(void)
{
    static const char expected[] =
        "\x1b[HMalbolge Snake - Linux / classic budget\n"
        "+------------+\n"
        "|            |\n"
        "|            |\n"
        "|            |\n"
        "|            |\n"
        "|    oo@  *  |\n"
        "|            |\n"
        "|            |\n"
        "|            |\n"
        "+------------+\n"
        "Score: 0  WASD + Enter, q quits\n";
    SnakeGame game;

    initialize_game(&game);
    captured_expected = expected;
    captured_count = 0U;
    captured_mismatch = 0U;
    render_game(&game);
    return captured_mismatch == 0U &&
        expected[captured_count] == '\0';
}

static unsigned int test_growth_and_direction(void)
{
    SnakeGame game;
    unsigned int step = 0U;

    initialize_game(&game);
    if (update_direction(&game, 97U) != 0U ||
        game.direction != DIRECTION_RIGHT)
    {
        return 0U;
    }
    while (step < 3U)
    {
        if (update_direction(&game, 100U) == 0U)
        {
            return 0U;
        }
        step_game(&game);
        ++step;
    }
    return game.game_over == 0U && game.length == 4U && game.score == 1U &&
        game.snake_x[0] == 9U && game.snake_y[0] == 4U &&
        game.snake_x[1] == 8U && game.snake_x[2] == 7U &&
        game.snake_x[3] == 6U && game.food_seed == 300U &&
        game.food_x == 0U && game.food_y == 1U;
}

static unsigned int wall_collision(unsigned int direction,
                                   unsigned int x, unsigned int y)
{
    SnakeGame game;

    initialize_game(&game);
    game.snake_x[0] = x;
    game.snake_y[0] = y;
    game.length = 1U;
    game.direction = direction;
    step_game(&game);
    return game.game_over == 1U;
}

static unsigned int test_self_collision(void)
{
    SnakeGame game;

    initialize_game(&game);
    game.length = 5U;
    game.direction = DIRECTION_LEFT;
    game.snake_x[0] = 2U;
    game.snake_y[0] = 2U;
    game.snake_x[1] = 2U;
    game.snake_y[1] = 3U;
    game.snake_x[2] = 1U;
    game.snake_y[2] = 3U;
    game.snake_x[3] = 1U;
    game.snake_y[3] = 2U;
    game.snake_x[4] = 1U;
    game.snake_y[4] = 1U;
    step_game(&game);
    return game.game_over == 1U;
}

static unsigned int test_tail_entry_is_legal(void)
{
    SnakeGame game;

    initialize_game(&game);
    game.length = 4U;
    game.direction = DIRECTION_LEFT;
    game.snake_x[0] = 2U;
    game.snake_y[0] = 2U;
    game.snake_x[1] = 2U;
    game.snake_y[1] = 3U;
    game.snake_x[2] = 1U;
    game.snake_y[2] = 3U;
    game.snake_x[3] = 1U;
    game.snake_y[3] = 2U;
    game.food_x = 11U;
    game.food_y = 7U;
    step_game(&game);
    return game.game_over == 0U && game.snake_x[0] == 1U &&
        game.snake_y[0] == 2U && game.length == 4U;
}

static unsigned int test_food_skips_occupied_candidate(void)
{
    SnakeGame game;

    initialize_game(&game);
    game.length = 1U;
    game.snake_x[0] = 0U;
    game.snake_y[0] = 1U;
    game.food_seed = 17U;
    place_food(&game);
    return game.game_over == 0U && game.food_seed == 5111U &&
        game.food_x == 11U && game.food_y == 1U;
}

int main(void)
{
    SnakeGame game;

    initialize_game(&game);
    if (initial_state_is_exact(&game) == 0U)
    {
        return parity_fail(1U);
    }
    if (test_initial_render() == 0U)
    {
        return parity_fail(2U);
    }
    if (test_growth_and_direction() == 0U)
    {
        return parity_fail(3U);
    }
    if (wall_collision(DIRECTION_RIGHT, 11U, 4U) == 0U)
    {
        return parity_fail(4U);
    }
    if (wall_collision(DIRECTION_LEFT, 0U, 4U) == 0U)
    {
        return parity_fail(5U);
    }
    if (wall_collision(DIRECTION_UP, 6U, 0U) == 0U)
    {
        return parity_fail(6U);
    }
    if (wall_collision(DIRECTION_DOWN, 6U, 7U) == 0U)
    {
        return parity_fail(7U);
    }
    if (test_self_collision() == 0U)
    {
        return parity_fail(8U);
    }
    if (test_tail_entry_is_legal() == 0U)
    {
        return parity_fail(9U);
    }
    if (test_food_skips_occupied_candidate() == 0U)
    {
        return parity_fail(10U);
    }

    parity_text("SNAKE-PARITY-v1\nOK\n");
    return 0;
}
