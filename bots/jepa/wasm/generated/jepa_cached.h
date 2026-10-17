/* Generated ABI; checkpoint tensors retain their original values. */
#include <stddef.h>
/* K/V arrays use contiguous [head=4][context=25][width=16]. */
void jepa_context_set_buf(size_t index, void *ptr);
void jepa_context_net(float *z96, float *k0_1600, float *v0_1600,
    float *k1_1600, float *v1_1600, float *value1,
    float *state73, int *ids24, float *feats504, float *mask24);
void jepa_predict4_set_buf(size_t index, void *ptr);
void jepa_predict4_net(float *latent384, float *logits4,
    float *z96, float *k0_1600, float *v0_1600, float *k1_1600, float *v1_1600,
    float *mask24, float *actions248, int *action_ids4, int *horizon1);
