function w = quantize(w, states, scheme)
%QUANTIZE Error source 2: a device resolves finitely many states.
%   W = ERR.QUANTIZE(W, STATES, SCHEME) snaps weights to the lattice a legal
%   combination of device states can reach, for SCHEME "differential" or "offset".
%
%   The knob spanning the two device families this repo treats as one model: an MTJ
%   is typically binary or few-level, a domain-wall device resolves more.
%
%   Applies at the **effective weight**, over the reachable set -- not to each
%   device in isolation. The devices are what have finite states; the programmer
%   knows the target weight and picks the states that best represent it.
%
%   Rounding each rail independently looks equivalent and is not. Two-state devices
%   with a target of w = 0.3: the positive rail rounds up, the negative rounds down,
%   and the pair lands on +1 where the nearest representable weight is 0. That is
%   the differential pair reduced to a sign bit, at twice the device count of an
%   offset. It was the first implementation on both sides of this seam and the
%   round-trip test is what caught it.
%
%   Reachable set: STATES levels for an offset, 2*STATES-1 for a pair, since the
%   effective weight is a *difference* of two device states.
%
%   Written fresh rather than inherited. photonn's err.quantize wraps to [0, 2*pi)
%   and iterates phase_fields, both phase-specific; the planning note claiming it
%   transfers "directly" was wrong. A conductance range is bounded, not cyclic, and
%   a cyclic quantiser here would map the largest weight onto the smallest -- not a
%   subtle error, but one that returns a plausible accuracy rather than failing.
    if isempty(states) || states <= 0, return; end
    if states < 2
        error("err:quantize:tooFewStates", ...
            "states_per_device must be at least 2; got %g.", states);
    end

    n = states - 1;
    if scheme == "differential"
        w = round(w * n) / n;
    else
        w = 2 * round((1 + w) / 2 * n) / n - 1;
    end
end
