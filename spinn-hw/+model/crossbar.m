function out = crossbar(handoff, opts)
%CROSSBAR Run the as-built crossbar forward pass over the frozen test set.
%   OUT = MODEL.CROSSBAR(HANDOFF) reproduces the ideal forward pass from a handoff
%   struct (io.read_handoff) and returns OUT with fields accuracy, predictions
%   (0-based, matching the Python labels), logits and labels.
%
%   OUT = MODEL.CROSSBAR(HANDOFF, OPTS) applies error-model overrides:
%     OPTS.conductances - nRows-by-nCols-by-nDev, replacing the ideal programming.
%                         This is what every +err device source perturbs.
%     OPTS.voltages     - n-by-nRows, replacing the ideal drive.
%     OPTS.currents     - n-by-nCols-by-nDev, replacing the summation itself.
%                         IR drop enters here rather than through voltages: what
%                         a cell actually sees depends on where it sits, so the
%                         correction is per device and cannot be written as a
%                         per-row drive.
%     OPTS.subset       - indices into the test set, for speed.
%
%   Patterned on photonn's model.evaluate, which is where the shape of this comes
%   from -- an ideal path with a documented set of overrides, so an error source
%   can never reach anything the ideal path does not also use.
%
%   Logits are returned in the trained scale: the decode divides out the window
%   and the drive, and readout_gain restores what training fitted. Accuracy does
%   not depend on the gain (argmax is scale-invariant) but any margin does.
    if nargin < 2, opts = struct(); end

    images = handoff.test_set.images;
    labels = handoff.test_set.labels(:);
    if isfield(opts, "subset") && ~isempty(opts.subset)
        images = images(:, :, opts.subset);
        labels = labels(opts.subset);
    end

    if isfield(opts, "voltages") && ~isempty(opts.voltages)
        V = opts.voltages;
    else
        V = model.encode(handoff, images);
    end

    if isfield(opts, "conductances") && ~isempty(opts.conductances)
        G = opts.conductances;
    else
        G = model.program(handoff);
    end

    if isfield(opts, "currents") && ~isempty(opts.currents)
        I = opts.currents;
    else
        % Kirchhoff, and nothing else: every device on a column adds its current
        % to the same wire.
        nDev = size(G, 3);
        I = zeros(size(V, 1), handoff.geometry.n_cols, nDev);
        for d = 1:nDev
            I(:, :, d) = V * G(:, :, d);
        end
    end

    gmin = handoff.operating_point.g_min_s;
    span = handoff.operating_point.g_max_s - gmin;
    scale = handoff.operating_point.read_voltage_v * span;

    if handoff.scheme == "differential"
        logits = (I(:, :, 1) - I(:, :, 2)) / scale;
    else
        % One rail, so the column carries a baseline set by the inputs rather than
        % by the weights. Subtracted exactly here; in hardware it is a real
        % current whose noise does not subtract, which is half the argument for
        % the differential pair.
        pedestal = sum(V, 2) * (gmin + span / 2);
        logits = (I(:, :, 1) - pedestal) / (scale / 2);
    end
    logits = logits * handoff.operating_point.readout_gain;

    [~, idx] = max(logits, [], 2);
    predictions = idx - 1;                      % 0-based, as Python labels are

    out.accuracy    = mean(predictions == labels);
    out.predictions = predictions;
    out.logits      = logits;
    out.labels      = labels;
end
