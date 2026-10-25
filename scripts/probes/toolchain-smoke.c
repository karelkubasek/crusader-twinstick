/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int *values = calloc(4, sizeof(*values));
    if (!values)
        return 1;
    for (int i = 0; i < 4; ++i)
        values[i] = i + 1;
    int sum = values[0] + values[1] + values[2] + values[3];
    free(values);
    if (sum != 10)
        return 1;
    puts("C compiler and C runtime: OK");
    return 0;
}
