/**
 * Copyright (C) PlatformIO <contact@platformio.org>
 * See LICENSE for details.
 */

#include <avr/io.h>

int main (void)
{
    /* Configure SW0 as input */
    PORTB.DIRCLR = PIN2_bm;
    /* Configure LED0 pin as output */
    PORTB.DIRSET = PIN5_bm;

    while (1)
    {
        /* Check the status of SW0 */
        /* 0: Pressed */
        if (!(PORTB.IN & (PIN2_bm)))
        {
            /* LED0 on */
            PORTB.OUTSET = PIN5_bm;
        }
        /* 1: Released */
        else
        {
            /* LED0 off */
            PORTB.OUTCLR = PIN5_bm;
        }
    }
}
