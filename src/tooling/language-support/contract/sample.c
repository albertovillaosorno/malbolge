// Copyright © 2026 Alberto Villa Osorno.
// SPDX-License-Identifier: MIT
//
// Candidate source for the future GitHub Linguist Malbolge sample.
// The final sample is the compiler-produced Malbolge artifact, not this C file.

enum
{
    MALBOLGE_TRITS = 10,
    MALBOLGE_MAX_WORD = 59048,
    MALBOLGE_HIGH_TRIT_WEIGHT = 19683,
    PROBE_COUNT = 6
};

static unsigned int rotate_word(unsigned int value)
{
    return value / 3u + (value % 3u) * MALBOLGE_HIGH_TRIT_WEIGHT;
}

static unsigned int crazy_word(unsigned int data, unsigned int accumulator)
{
    static const unsigned char crazy_digit[3][3] = {
        {1u, 0u, 0u},
        {1u, 0u, 2u},
        {2u, 2u, 1u},
    };
    unsigned int result = 0u;
    unsigned int place = 1u;

    for (unsigned int trit = 0u; trit < MALBOLGE_TRITS; ++trit)
    {
        const unsigned int data_trit = data % 3u;
        const unsigned int accumulator_trit = accumulator % 3u;
        result +=
            (unsigned int)crazy_digit[data_trit][accumulator_trit] * place;
        data /= 3u;
        accumulator /= 3u;
        place *= 3u;
    }

    return result;
}

static unsigned int advance_word(unsigned int value)
{
    if (value == MALBOLGE_MAX_WORD)
    {
        return 0u;
    }
    return value + 1u;
}

static unsigned int mix_probe(unsigned int state, unsigned int input)
{
    const unsigned int rotated = rotate_word(input);
    const unsigned int mixed = crazy_word(rotated, state);
    return advance_word(mixed);
}

static unsigned int run_probe(void)
{
    static const unsigned int probes[PROBE_COUNT] = {
        0u, 1u, 2u, 42u, 19683u, MALBOLGE_MAX_WORD,
    };
    unsigned int state = 0u;

    for (unsigned int index = 0u; index < PROBE_COUNT; ++index)
    {
        state = mix_probe(state, probes[index]);
    }

    return state;
}

int main(void)
{
    return (int)(run_probe() % 256u);
}
