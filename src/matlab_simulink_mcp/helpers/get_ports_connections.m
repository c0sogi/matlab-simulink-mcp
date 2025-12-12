function [inports, outports, simscapeports, connections] = get_ports_connections(blk, blk_name, blk_type)

% This function gets, for a given block, its name and type, the names (if
% it's a subsystem) and tags of its ports and connections.

inports = {};
outports = {};
simscapeports = {};
connections = {};

is_subsystem = strcmp(blk_type, 'SubSystem');
PC = get_param(blk, 'PortConnectivity');

% First create a list of the port names. Unfortunately, this is only
% possible for subsystems since only port blocks can have names, not ports themselves

% For non-Simscape port blocks, the order through find_system is the
% same as the ports in PortConnectivity matrix

% For Simscape port blocks, the order through find_system is based on the
% number of the port (displayed visually at the center of PortConnection block)
% But in PortConnectivity matrix, the ports on Left are listed first and then right
% Within each type, the order follows the visual number of the port
% So we first get port blocks on left, and then right, and then concenate all of them

if is_subsystem
    
    SimulinkPortBlks = find_system(blk, 'Regexp', 'on', 'BlockType', ...
        'Inport|Outport|EnablePort|TriggerPort|ResetPort|ActionPort');
    
    PhyPortBlksLefts = find_system(blk, 'Regexp', 'on', 'BlockType', 'PMIOPort', 'Side', 'Left');
    PhyPortBlksRights = find_system(blk, 'Regexp', 'on', 'BlockType', 'PMIOPort', 'Side', 'Right');

    PortBlks = [SimulinkPortBlks(:); PhyPortBlksLefts(:); PhyPortBlksRights(:)];
    PortNames = get_param(PortBlks, 'Name');

    if isempty(PortNames)
        is_subsystem = 0;
    end 

end 

% Some Simscape blocks e.g. PS-Simulink Convertor are defined internally as
% SubSystems instead of Simscape blocks. So the if condition above ensures
% that if such blocks are counted as subsystems and port names gathered
% (which would be empty), we flag the block manually as not a subsystem

% Loop through the ports. For each port, create a strcuture with tag and
% name (if the element is a subsystem) fields
% For connections, first get the Simscape ports (i.e. LConnX and % RConnX).
% For these ports, DstPort contains the handle of the attached port. So we
% get the DstBlock's PortHandles through its handle, and then get its tag
% For non-simscape ports, the DstPort contains -1 the field index of the
% attached port in the DstBlock's PortConnectivity matrix.
% Also, only consider outports for these ports as they are easily
% distinguishable through an empty SrcBlock. For inports, the connections
% will be gathered when the script is ran for the connected block. This
% also prevents repitition. Inports also include ports such as trigger etc

for i = 1:length(PC)
    
    Port = PC(i).Type;  
    PortStr = struct('tag', Port);
    if is_subsystem
        try
            PortStr.name = PortNames{i};
        catch 
        end 
    end

    if contains(Port, {'LConn', 'RConn'})
        
        simscapeports{end+1} = PortStr;

        for j = 1:length(PC(i).DstBlock)
            
            DstBlockHandle = PC(i).DstBlock(j);
            DstBlockName = get_param(DstBlockHandle, 'Name');
            
            DstPortHandle = PC(i).DstPort(j);
            DstPH = get_param(DstBlockHandle, 'PortHandles');
               
            idxL = find(DstPH.LConn == DstPortHandle, 1);
            idxR = find(DstPH.RConn == DstPortHandle, 1);
                
            if ~isempty(idxL)
                DstPort = sprintf('LConn%d', idxL);
            else
                DstPort = sprintf('RConn%d', idxR);
            end
                
            connections{end+1} = struct('from', sprintf("%s/%s", blk_name, Port), ...
                'to', sprintf("%s/%s", DstBlockName, DstPort));
        
        end 
    
    else 
        
        if isempty(PC(i).SrcBlock) 
            
            outports{end+1} = PortStr;
            
            for j = 1:length(PC(i).DstBlock)
   
                DstBlockHandle = PC(i).DstBlock(j);
                DstBlockName = get_param(DstBlockHandle, 'Name');

                DstPortField = PC(i).DstPort(j) + 1;
                DstPC = get_param(DstBlockHandle, 'PortConnectivity');
                DstPort = DstPC(DstPortField).Type;
                
                connections{end+1} = struct('from', sprintf("%s/%s", blk_name, Port), ...
                    'to', sprintf("%s/%s", DstBlockName, DstPort));
            
            end 
       
        else

            inports{end+1} = PortStr;

        end
    end
end
end 
