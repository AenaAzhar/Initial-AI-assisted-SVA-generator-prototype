// Simple synchronous FIFO, parameterised on DEPTH and WIDTH.
// Active-low synchronous reset.

module fifo #(
    parameter int DEPTH = 8,
    parameter int WIDTH = 8
) (
    input  logic              clk,
    input  logic              rst_n,
    input  logic              push,
    input  logic              pop,
    input  logic [WIDTH-1:0]  din,
    output logic [WIDTH-1:0]  dout,
    output logic              empty,
    output logic              full
);
    localparam int ADDR_W = $clog2(DEPTH);

    logic [WIDTH-1:0]   mem [DEPTH];
    logic [ADDR_W-1:0]  wr_ptr;
    logic [ADDR_W-1:0]  rd_ptr;
    logic [ADDR_W:0]    count;

    assign empty = (count == 0);
    assign full  = (count == DEPTH);
    assign dout  = mem[rd_ptr];

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            wr_ptr <= '0;
            rd_ptr <= '0;
            count  <= '0;
        end else begin
            case ({push && !full, pop && !empty})
                2'b10: begin
                    mem[wr_ptr] <= din;
                    wr_ptr <= wr_ptr + 1;
                    count  <= count + 1;
                end
                2'b01: begin
                    rd_ptr <= rd_ptr + 1;
                    count  <= count - 1;
                end
                2'b11: begin
                    mem[wr_ptr] <= din;
                    wr_ptr <= wr_ptr + 1;
                    rd_ptr <= rd_ptr + 1;
                end
                default: ;
            endcase
        end
    end
endmodule