library IEEE;
use IEEE.STD_LOGIC_1164.ALL;
use IEEE.NUMERIC_STD.ALL;
use IEEE.MATH_REAL.ALL;

entity series_signal_generator is

  Generic (
        FFT_Size : integer := 256;
        N_bits : integer := 16;
        N_chan : integer := 8
  );
  Port (
        i_bit_clk : in std_logic;
        
        o_bit_clk : out std_logic;
        o_f_sync : out std_logic;
        o_data : out std_logic_vector(N_chan-1 downto 0)
   );
end series_signal_generator;

architecture Behavioral of series_signal_generator is
    type LUT_TYPE is array (0 to FFT_Size-1) of std_logic_vector(N_bits-1 downto 0);
    type theta_TYPE is array (0 to N_chan-1) of integer range 0 to FFT_Size-1;
    signal cos_LUT, sin_LUT, sinc_LUT, rect_LUT, rampa_LUT : LUT_TYPE;
    signal theta_index      : theta_TYPE := (others => 0);
    signal bit_counter : integer range 0 to N_bits-1 := 0;
    signal data_temp : integer range -2**(N_bits-1) to 2**(N_bits-1)-1;
    
begin

    -- Generate LUT values at elaboration time
    process
        variable angle : real;
        variable center : integer := FFT_Size / 2;
    begin
        for i in 0 to FFT_Size-1 loop
            angle := (2.0 * MATH_PI * real(i)) / real(FFT_Size);
            cos_LUT(i) <= std_logic_vector(to_signed(integer(round(real(2**(N_bits-1)-1) * cos(angle))), N_bits));
            sin_LUT(i) <= std_logic_vector(to_signed(integer(round(real(2**(N_bits-1)-1) * sin(angle))), N_bits));
            if i = 0 then
                sinc_LUT(i) <= (N_bits-1 downto 0 => '0');
            else
                sinc_LUT(i) <= std_logic_vector(to_signed(integer(round(real(2**(N_bits-1)-1) * sin(angle-4.0*2.0*3.14) / (angle-4.0*2.0*3.14))), N_bits));
            end if;
            
            if i > (FFT_Size / 2)-3 and  i < (FFT_Size / 2)+3 then
                rect_LUT(i) <= std_logic_vector(to_signed(2**(N_bits-1)-1, N_bits));
            else
                rect_LUT(i) <= (N_bits-1 downto 0 => '0');
            end if;
        end loop;
        wait;
    end process;
    
    -- Proceso principal
    process(i_bit_clk)
    begin
        if rising_edge(i_bit_clk) then
            
            for i in 0 to N_chan-1 loop
                o_data(i) <= rampa_LUT(theta_index(i))(N_bits-1 - bit_counter);
                
                if bit_counter = N_bits-1 then
                    theta_index(i) <= (theta_index(i) + 1 + i) mod FFT_Size;
                    bit_counter <= 0;
                else 
                    bit_counter <= bit_counter +1;            
                end if;  
            end loop;
            
            -- si el valor anterior de bit counter no es el máximo, no hay que actualizar el theta index, y se saca el bit que toque de la lut.
            if bit_counter = 0 then 
                -- Empezamos palabra de N_bits bits
                o_f_sync <= '1';
            else 
                o_f_sync <= '0';
            end if;
                        
            
       end if;
    end process;
    
    o_bit_clk <= i_bit_clk;   
end Behavioral;
