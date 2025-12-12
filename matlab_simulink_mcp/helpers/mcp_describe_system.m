function system_data = mcp_describe_system(system_path, main_system, open)
%DESCRIBE_SYSTEM Describe a system layout for MCP consumption.
% Returns a JSON string that matches the Pydantic schema in `types.py`:
% - SystemDescription.Elements: list[Element]
% - SystemDescription.Connections: list[Connection] with keys From/To
% - Port fields: name/index/type (type optional)

    % Load model (best-effort)
    try
        load_system(main_system);
    catch
        try
            load_system([main_system, '.slx']);
        catch
        end
    end

    if open
        try
            open_system(system_path);
        catch
        end
    end

    blocks = find_system(system_path, 'SearchDepth', 1, 'Type', 'Block');

    elements = repmat(struct(), 0, 1);
    connections = repmat(struct('From', '', 'To', ''), 0, 1);

    for i = 1:length(blocks)
        blk = blocks{i};

        % Skip the system itself when describing a subsystem
        if strcmp(blk, system_path)
            continue;
        end

        element = struct();
        element.Name = get_param(blk, 'Name');
        blkType = get_param(blk, 'BlockType');
        element.Type = blkType;

        % Reference block (optional)
        blkSource = '';
        try
            blkSource = get_param(blk, 'ReferenceBlock');
        catch
        end
        if ~isempty(blkSource) && ~strcmp(char(blkSource), '')
            element.Source = blkSource;
        end

        % Normalize non-SubSystem/non-Simscape blocks into generic "Block"
        if ~strcmp(element.Type, "SimscapeBlock") && ~strcmp(element.Type, "SubSystem") && ~contains(element.Type, "Port", 'IgnoreCase', true)
            element.Type = "Block";
            if isempty(blkSource) || strcmp(char(blkSource), '')
                element.Source = ['built-in/', blkType];
            end
        end

        % Ports + connections
        [inports, outports, simscapeports, connects] = get_ports_connections(blk, element.Name, blkType);

        inP = local_ports(inports, []);
        outP = local_ports(outports, []);
        scP = local_ports(simscapeports, "Simscape");

        if ~isempty(inP), element.Inports = inP; end
        if ~isempty(outP), element.Outports = outP; end
        if ~isempty(scP), element.SimscapePorts = scP; end

        if ~isempty(connects)
            for k = 1:numel(connects)
                c = connects{k};
                if isfield(c, 'from') && isfield(c, 'to')
                    connections(end+1, 1) = struct('From', c.from, 'To', c.to); %#ok<AGROW>
                end
            end
        end

        elements(end+1, 1) = element; %#ok<AGROW>
    end

    system = struct();
    system.Elements = elements;
    system.Connections = connections;

    % Return JSON for stable cross-language interop (MATLAB -> Python)
    system_data = jsonencode(system);
end

function portsOut = local_ports(portCells, portType)
    if isempty(portCells)
        portsOut = repmat(struct(), 0, 1);
        return;
    end

    n = numel(portCells);
    portsOut = repmat(struct('name', '', 'index', 0, 'type', []), n, 1);

    for j = 1:n
        p = portCells{j};

        nm = '';
        if isfield(p, 'name')
            nm = p.name;
        end
        if isempty(nm) && isfield(p, 'tag')
            nm = p.tag;
        end
        if isempty(nm)
            nm = sprintf('Port%d', j);
        end

        idx = j;
        if isfield(p, 'tag')
            m = regexp(char(p.tag), '\\d+$', 'match', 'once');
            if ~isempty(m)
                v = str2double(m);
                if ~isnan(v)
                    idx = v;
                end
            end
        end

        portsOut(j).name = char(nm);
        portsOut(j).index = idx;
        if ~isempty(portType)
            portsOut(j).type = char(portType);
        else
            portsOut(j).type = [];
        end
    end
end
