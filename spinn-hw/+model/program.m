function G = program(handoff, weights, states)
%PROGRAM Map weights in [-1, 1] onto device conductances.
%   G = MODEL.PROGRAM(HANDOFF) uses the handoff's own weights, unquantised.
%   G = MODEL.PROGRAM(HANDOFF, W) programs W instead.
%   G = MODEL.PROGRAM(HANDOFF, W, STATES) additionally restricts every device to
%   STATES levels -- error source 2, applied here because choosing which states
%   represent a weight is part of programming, not a perturbation of it.
%
%   G is nRows-by-nCols-by-nDev. The third axis is the device index within one
%   weight: two rails for a differential pair, one for an offset. Both schemes
%   present the same shape downstream, so nothing after this has to branch.
%
%   A pair is (max(w,0), max(-w,0)) of the span -- one rail carries the weight and
%   the other is off -- with w the integer level k over states-1 when quantised and
%   the weight itself when not. So the continuous pair is the limit of the quantised
%   one. It draws the least current a weight allows, and its zero is two devices
%   off, which matters because the measured spread of this device class is
%   proportional to conductance (Doevenspeck et al. 2020). Until 2026-10-04 the
%   continuous pair was centred, (1 +/- w)/2, while the quantised one was not; the
%   effective weights were identical, so no accuracy showed it, and every source
%   that sees the rails did. docs/history.md has the account.
%
%   The handoff carries weights and not rails, so this convention is not checked
%   by the round trip's accuracy: tests/test_handoff_roundtrip.py pins this G to
%   Python's rails directly.
%
%   Mirrors spinn/crossbar.py:Crossbar.program, including its rounding convention:
%   both sides round half away from zero. MATLAB's round already does; NumPy's
%   rounds half to even, so the Python side uses an explicit helper. They differ
%   only on exact halves -- which is exactly where a weight sits between two device
%   states, so left alone the two sides would quantise it differently, agree on
%   everything else, and disagree on an accuracy with nothing to point at.
    if nargin < 2 || isempty(weights), weights = handoff.parameters.weights; end
    if nargin < 3, states = []; end

    w = max(min(weights, 1), -1);
    gmin = handoff.operating_point.g_min_s;
    span = handoff.operating_point.g_max_s - gmin;

    if isempty(states) || states <= 0
        if handoff.scheme == "differential"
            G = cat(3, gmin + max(w, 0) * span, ...
                       gmin + max(-w, 0) * span);
        else
            G = gmin + (1 + w) / 2 * span;
        end
        return
    end

    n = states - 1;
    if handoff.scheme == "differential"
        k = round(w * n);
        G = cat(3, gmin + max(k, 0) / n * span, ...
                   gmin + max(-k, 0) / n * span);
    else
        i = round((1 + w) / 2 * n);
        G = gmin + i / n * span;
    end
end
