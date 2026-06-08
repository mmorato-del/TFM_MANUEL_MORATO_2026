
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;


entity FFT_buffer is
  Generic (
    FFT_size : integer := 256;
    N_bits : integer := 16;
    N_chan : integer := 8
  );
  Port (
    i_clk : in std_logic;
    i_word_valid : in std_logic;
    i_word : in std_logic_vector(N_chan*N_bits-1 downto 0);
    
    
    o_tvalid : out std_logic;
    o_tlast : out std_logic;
    o_word : out std_logic_vector(N_bits-1 downto 0)
  );
end FFT_buffer;

architecture Behavioral of FFT_buffer is
    type FFT_multichannel_window is array (0 to FFT_size-1) of std_logic_vector(N_chan*N_bits-1 downto 0); 
    signal FFT_shift_register : FFT_multichannel_window := (others => (others => '0'));
    signal FFT_points_count : integer range 0 to FFT_size-1 := 0;
    signal FFT_chan_count : integer range 0 to N_chan-1 :=0;
    signal trans_enable : std_logic := '0';
begin
    process(i_clk) 
    begin
        if rising_edge(i_clk) then
            -- Proceso de lectura, cuando se recibe un dato.
            if i_word_valid = '1' then
                -- Entra una palabra nueva en el registro.
                --FFT_shift_register <= FFT_shift_register(FFT_size-2 downto 0) & i_word; CRUCE INCORRECTO DE TO CON DOWNTO
                FFT_shift_register <= i_word & FFT_shift_register( 0 to FFT_size-2);
                 -- Comienza la transmisión de los 256 puntos del primer canal
                trans_enable <= '1';
            end if;
            
            -- Comienza la transmisión de los 256 puntos del primer canal
            if trans_enable = '1' then
                -- Se saca un punto de un canal, correspondiente al estado de los contadores.
                o_word <= FFT_shift_register(FFT_points_count)((FFT_chan_count+1)*N_bits-1 downto FFT_chan_count*N_bits); 
                o_tvalid <= '1';
                
                -- Recorrido de la tabla. 
                if FFT_points_count = FFT_size-1 then
                    o_tlast <= '1';
                    if FFT_chan_count = N_chan-1 then
                        --Fin de transmisión
                        trans_enable <= '0';
                        FFT_points_count <= 0;
                        FFT_chan_count <= 0;
                    else
                        FFT_points_count <= 0;
                        FFT_chan_count <= FFT_chan_count +1;
                    end if;
                else
                    FFT_points_count <= FFT_points_count +1;
                    o_tlast <= '0';
                end if;  
                
                -- Gestión de tlast. No se puede poner en el bucle anterior porque tiene que ir con el último punto, no con el primero del siguiente.
                --if FFT_points_count = FFT_size-1 then
                --    o_tlast <= '1';
                --else
                --    o_tlast <= '0';
                --end if;
                
            else -- SI NO ESTÁ HABILITADA LA TRANSMISION
                o_tlast <= '0';
                o_tvalid <= '1';
            end if;
        
        --trans_enable es equivalente a tvalid.
        o_tvalid <= trans_enable;  
            
        end if;
    end process;

end Behavioral;