function G = area_variation(G, sigmaRel, seed)
%AREA_VARIATION A device-to-device spread proportional to conductance.
%   G = ERR.AREA_VARIATION(G, SIGMAREL, SEED) multiplies every device's conductance
%   by its own factor a ~ N(1, SIGMAREL), drawn once per device.
%
%   This is the spread imec measured on this device class -- three-terminal SOT
%   junctions read through the barrier (Doevenspeck et al., VLSI 2020). Its
%   sigma/mu "does not increase for increasing RA products" and is "mostly
%   determined by process-induced area variations": a pillar a little smaller than
%   drawn has a proportionally smaller conductance, in whatever state it holds. So
%   the factor scales the device, not its state, and SIGMAREL is that paper's
%   sigma/mu directly.
%
%   Error source 1 (err.conductance_variation) is a different model of the same
%   physical fact: a uniform sigma against the span, added and clamped. It stays
%   the row's required precision, in the hub's effective bits. This source is the
%   one a measured spread can be put against, and the two are never stacked: they
%   are two descriptions of one spread, not two spreads.
%
%   No clamp to the window, deliberately. Clamping is right for a programming
%   error, because a device cannot be set outside the states it has. It is wrong
%   here: a smaller pillar has a lower g_min *and* a lower g_max, so a device can
%   land below the nominal window, and that is the spread rather than an artefact.
%   The factor is floored at zero, because an area cannot be negative; at the
%   largest sigma/mu swept (0.15) that floor is 6.7 sigma away and is never reached.
%
%   Gaussian on the conductance, where imec's model is Gaussian on the radius.
%   Area goes as r^2, which skews the factor by O(sigma^2); at the sigma/mu this
%   budget sweeps the two agree to first order, and the measured quantity is
%   sigma/mu itself, so that is the parameter.
%
%   Every device gets its own draw. Under a differential pair the two rails are two
%   pillars and are drawn independently. Under the pair's (max(w,0), max(-w,0))
%   representation a zero weight is two devices at g_min, the state where this
%   spread is smallest in absolute terms -- which is why that representation was
%   chosen (docs/history.md, 2026-10-04).
    if sigmaRel <= 0, return; end

    s = RandStream('twister', 'Seed', seed);
    a = max(1 + sigmaRel * randn(s, size(G)), 0);
    G = G .* a;
end
