library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;



entity deserializer_v2 is
  Generic (
    N_bits : integer := 16;
    N_chan : integer := 8
  );
  Port ( 
    i_bit_clk : in std_logic;
    i_frame_sync : in std_logic;
    i_data : in std_logic_vector(N_chan-1 downto 0);
    i_fpga_clk : in std_logic;
    
    o_word_valid : out std_logic;
    o_word : out std_logic_vector(N_chan*N_bits-1 downto 0);
    
    --DEBUG
    o_bit_count_debug : out std_logic_vector(3 downto 0);
    o_word_valid_slow : out std_logic
  );
end deserializer_v2;

architecture Behavioral of deserializer_v2 is
    signal r1_bit_clk, r2_bit_clk, r3_bit_clk : std_logic;
    signal r1_frame_sync, r2_frame_sync : std_logic;
    signal bit_count : integer range 0 to N_bits-1 := 0;
    signal shift_register : std_logic_vector(N_chan*N_bits-1 downto 0) := (others => '0');
    signal prev_word_valid, actual_word_valid : std_logic; -- SALIDA PULSO RAPIDO
begin
    process (i_fpga_clk)
    begin
        o_bit_count_debug <= std_logic_vector(to_unsigned(bit_count,4));
        
        if rising_edge(i_fpga_clk) then 
        
            prev_word_valid <= actual_word_valid;
            
            r1_bit_clk <= i_bit_clk;
            r2_bit_clk <= r1_bit_clk;
            r3_bit_clk <= r2_bit_clk;
            
            r1_frame_sync <= i_frame_sync;
            r2_frame_sync <= r1_frame_sync;
            
            if r3_bit_clk = '0' and r2_bit_clk = '1' then
                for i in 0 to N_chan-1 loop
                    --shift_register(i) <= shift_register(i)(N_bits-2 downto 0) & i_data(i);
                    shift_register((i+1)*N_bits-1 downto i*N_bits) <= shift_register((i+1)*N_bits-2 downto i*N_bits) & i_data(i);    
                end loop;
        
                if r2_frame_sync = '1' then
                    bit_count <= 0;
                else
                    bit_count <= bit_count +1;
                end if;
                
                if bit_count = N_bits-1 then
                    --o_word_valid <= '1';
                    o_word_valid_slow <= '1';
                    actual_word_valid <= '1';
                    o_word <= shift_register;
                else
                    --o_word_valid <= '0';
                    o_word_valid_slow <= '0';
                    actual_word_valid <= '0';
                end if;
                
            end if;
            
            if prev_word_valid = '0' and actual_word_valid = '1' then
                o_word_valid <= '1';
            else
                o_word_valid <= '0';
            end if;
        end if;
    
    end process;

end Behavioral;
