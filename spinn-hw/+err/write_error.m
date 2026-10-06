function G = write_error(G, rate, states, handoff, seed)
%WRITE_ERROR Devices written to a neighbouring level instead of the one intended.
%   G = ERR.WRITE_ERROR(G, RATE, STATES, HANDOFF, SEED) takes conductances fresh
%   from model.program at STATES levels per device, and moves every device that
%   was programmed to an *intermediate* level to the level above or below it, each
%   with probability RATE/2, independently per device.
%
%   This is the error that sets a magnetic junction apart from the other analog
%   memories: its switching is stochastic. imec's multi-pillar SOT-MRAM selects a
%   level by how many of four pillars a write current switches (Doevenspeck et al.,
%   VLSI 2021). Their Fig. 11(a) is the per-attempt probability of landing on the
%   intended level, over 80 devices, and their Fig. 9 shows where a miss goes:
%   to the two neighbouring levels, about equally. Hence the model:
%
%     - level 0 never moves. It is the reset state, all pillars antiparallel, and a
%       device meant to stay there receives no write pulse at all;
%     - level n = STATES-1 never moves. Fig. 11(a) has it at 1.00 on every device;
%     - every level between moves to j-1 or j+1, each half the time, with
%       probability RATE. RATE is what is left after the attempts the programmer
%       is willing to spend, so it is not the paper's per-attempt figure but that
%       figure's complement raised to the number of verified attempts.
%
%   Applied straight after programming and before any spread: a device is written
%   to some level, possibly the wrong one, and *then* its conductance deviates from
%   that level's nominal value. The level is recovered from G exactly, which is
%   only possible on the lattice program() produces, so anything else is refused.
%
%   Every device gets a draw whether or not its level can move, so the draw a
%   device receives does not depend on what the other devices were programmed to.
%   Two weight matrices programmed from one seed see the same coin for the same
%   device, which is the property the driver's seed offsets exist to protect.
%
%   Under a differential pair the two rails are two devices, written separately,
%   and drawn independently. The pair stores a weight as one rail at its level and
%   the other at 0, so only the rail carrying the weight can be wrong, and a zero
%   weight cannot be.
    if isempty(states) || states < 2
        error('err:write_error:needsStates', ...
              'write errors are defined on levels; set states_per_device as well.');
    end

    n = states - 1;
    gmin = handoff.operating_point.g_min_s;
    span = handoff.operating_point.g_max_s - gmin;

    x = (G - gmin) / span * n;
    j = round(x);
    if max(abs(x(:) - j(:))) > 1e-9
        error('err:write_error:offLattice', ...
              ['G is not on the %d-level lattice. Write errors are applied straight ' ...
               'after model.program, before any spread.'], states);
    end
    if rate <= 0, return; end

    s = RandStream('twister', 'Seed', seed);
    miss = rand(s, size(G)) < rate;
    step = 2 * (rand(s, size(G)) < 0.5) - 1;

    movable = j > 0 & j < n;
    j = j + (miss & movable) .* step;
    G = gmin + j / n * span;
end
