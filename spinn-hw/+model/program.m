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
%   Under quantisation the pair is (max(k,0), max(-k,0)) for integer level k, which
%   is the representation drawing the least current. Centring the pair instead
%   would keep both devices further from their extremes; that is a real
%   alternative, not taken here, because the low-current choice is also the one
%   whose zero weight is two devices in the same state.
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
            G = cat(3, gmin + (1 + w) / 2 * span, ...
                       gmin + (1 - w) / 2 * span);
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
