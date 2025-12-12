function issues = mcp_validate_code(file_name)
%VALIDATE_CODE Run MATLAB Code Analyzer on a file and return issue messages.
% This function name must match the filename because the MCP server calls
% `eng.mcp_validate_code(...)`.

    try
        issues = {checkcode(file_name).message};
    catch
        issues = {'Failed to validate code.'};
    end
end