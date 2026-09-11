function G = conductance_variation(G, sigmaRel, handoff, seed)
%CONDUCTANCE_VARIATION Error source 1: sigma on the programmed state.
%   G = ERR.CONDUCTANCE_VARIATION(G, SIGMAREL, HANDOFF, SEED) perturbs every
%   device independently and clamps the result to the physical window.
%
%   SIGMAREL is expressed as a **fraction of the conductance span**, not in
%   siemens. That is deliberate and it is the whole reason the key is named
%   sigma_g_rel. The comparison unit for this project is
%
%       effective bits = log2(operating range / sigma)
%
%   which is dimensionless, so a tolerance quoted against the span converts
%   straight across: bits = -log2(sigma_g_rel). An absolute sigma would have to be
%   divided by the window before it meant anything, and the window is a design
%   choice that a different junction would change.
%
%   The counterpart of photonn's phase-shifter error, and the source most likely
%   to bind here: the window this has to fit inside is small.
%
%   Every device gets its own draw. Under a differential pair that is two draws
%   per weight, which is the cost side of that scheme -- the effective weight's
%   sigma is larger by sqrt(2) than a single device's, against a signed range that
%   is twice as wide.
%
%   Clamping at the window edge is physical, not defensive: a device cannot be
%   programmed outside the states it has. It also makes the error asymmetric for
%   weights already near an edge, which is a real effect and not a modelling
%   artifact.
    if sigmaRel <= 0, return; end

    s = RandStream('twister', 'Seed', seed);
    gmin = handoff.operating_point.g_min_s;
    gmax = handoff.operating_point.g_max_s;

    G = G + (sigmaRel * (gmax - gmin)) * randn(s, size(G));
    G = min(max(G, gmin), gmax);
end
