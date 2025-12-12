function mcp_format_system(varargin)
%FORMAT_SYSTEM Best-effort cleanup after running user MATLAB code.
% The MCP server calls this with no outputs; keep this function safe and
% dependency-free. Extra inputs are ignored for compatibility.

    %#ok<INUSD>
    try
        systems = find_system('type', 'block_diagram');
    catch
        return;
    end

    for i = 1:numel(systems)
        sys = systems{i};
        try
            hLines = find_system(sys, 'FindAll', 'on', 'Type', 'line', 'Connected', 'off');
            if ~isempty(hLines)
                delete_line(hLines);
            end
        catch
            % ignore cleanup failures
        end
    end
end
