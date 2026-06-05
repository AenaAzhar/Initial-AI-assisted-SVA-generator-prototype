// Round-robin arbiter for 4 requesters.

module arbiter #(
    parameter int N = 4
) (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [N-1:0] req,
    output logic [N-1:0] grant
);
    logic [$clog2(N)-1:0] last;

    always_ff @(posedge clk) begin
        if (!rst_n) begin
            last  <= '0;
            grant <= '0;
        end else begin
            grant <= '0;
            for (int i = 1; i <= N; i++) begin
                int idx = (last + i) % N;
                if (req[idx]) begin
                    grant[idx] <= 1'b1;
                    last <= idx[$clog2(N)-1:0];
                    break;
                end
            end
        end
    end
endmodule