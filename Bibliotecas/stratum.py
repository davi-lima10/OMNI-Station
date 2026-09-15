# ============================================================================
#  stratum — Terminal layout library
#  Aligned, colored output with ANSI escape sequences.
# ============================================================================


# ----------------------------------------------------------------------------
#  Core: visible length (ignores ANSI escapes)
# ----------------------------------------------------------------------------
def visible_len(text):
    """Count only visible characters. Ignores ANSI escape sequences."""
    n = 0
    in_escape = False
    for c in text:
        if c == '\x1b':
            in_escape = True
        elif in_escape:
            if c == 'm':
                in_escape = False
        else:
            n += 1
    return n


# ----------------------------------------------------------------------------
#  Padding
# ----------------------------------------------------------------------------
def pad(text, width):
    """Pad text to `width` VISIBLE characters (left-aligned)."""
    return text + ' ' * max(0, width - visible_len(text))


# ----------------------------------------------------------------------------
#  Text: print one or two columns, aligned
# ----------------------------------------------------------------------------
def text(left, gap, right='', sep='   '):
    """
    Print text in one or two columns.

    - `left`: content of the left column (string).
    - `gap`: visible width for the left column (int). Use `space_terminal`.
    - `right`: content of the right column (string, optional).
    - `sep`: separator between columns (default '   ').

    Examples:
        st.text(temperatura_string, space_terminal, entalpia_string)
        st.text(titulo_string, space_terminal)              # one column only
    """
    padded = pad(left, gap)
    if right:
        print(f"{padded}{sep}{right}")
    else:
        print(padded)


# ----------------------------------------------------------------------------
#  Rule: horizontal separator
# ----------------------------------------------------------------------------
def rule(char='─', width=35, color=''):
    """Return a horizontal rule string (uncolored by default)."""
    return f"{color}{char * width}\x1b[0m"


# ----------------------------------------------------------------------------
#  Clear: clear terminal screen and move cursor to top-left
# ----------------------------------------------------------------------------
def clear():
    """Clear terminal screen and move cursor to top-left."""
    print('\033[H\033[J', end='')