#include <tgmath.h>
#include <stddef.h>

void jepa_predict4_E_78_4n1(float* restrict data0_312, float* restrict data1_248, int* restrict data2_4, float* restrict data3_1024, float* restrict data4_512, float* restrict data5_976) {
  int val0 = (*(data2_4+0));
  int val1 = (*(data2_4+1));
  int val2 = (*(data2_4+2));
  int val3 = (*(data2_4+3));
  int alu0 = (val0*7);
  int alu1 = (alu0+3);
  int alu2 = (val1*7);
  int alu3 = (alu2+3);
  int alu4 = (val2*7);
  int alu5 = (alu4+3);
  int alu6 = (val3*7);
  int alu7 = (alu6+3);
  _Bool alu8 = (val0<0);
  int alu9 = (alu8?63:0);
  int alu10 = ((val0+alu9)>>6);
  int alu11 = ((alu8&((val0&63)!=0))?(alu10+-1):alu10);
  int alu12 = (val0+(alu11*-64));
  _Bool alu13 = (val1<0);
  int alu14 = (alu13?63:0);
  int alu15 = ((val1+alu14)>>6);
  int alu16 = ((alu13&((val1&63)!=0))?(alu15+-1):alu15);
  int alu17 = (val1+(alu16*-64));
  _Bool alu18 = (val2<0);
  int alu19 = (alu18?63:0);
  int alu20 = ((val2+alu19)>>6);
  int alu21 = ((alu18&((val2&63)!=0))?(alu20+-1):alu20);
  int alu22 = (val2+(alu21*-64));
  _Bool alu23 = (val3<0);
  int alu24 = (alu23?63:0);
  int alu25 = ((val3+alu24)>>6);
  int alu26 = ((alu23&((val3&63)!=0))?(alu25+-1):alu25);
  int alu27 = (val3+(alu26*-64));
  int alu28 = ((alu1<0)?1:0);
  int alu29 = (((int)(((((long long)(alu1))*1126548799ll)>>36ll)))+alu28);
  int alu30 = ((alu3<0)?1:0);
  int alu31 = (((int)(((((long long)(alu3))*1126548799ll)>>36ll)))+alu30);
  int alu32 = ((alu5<0)?1:0);
  int alu33 = (((int)(((((long long)(alu5))*1126548799ll)>>36ll)))+alu32);
  int alu34 = ((alu7<0)?1:0);
  int alu35 = (((int)(((((long long)(alu7))*1126548799ll)>>36ll)))+alu34);
  int alu36 = (((alu0<-3)&((alu1-(61*alu29))!=0))?(alu29+-1):alu29);
  int alu37 = (alu0+(alu36*-61));
  int alu38 = (((alu2<-3)&((alu3-(61*alu31))!=0))?(alu31+-1):alu31);
  int alu39 = (alu2+(alu38*-61));
  int alu40 = (((alu4<-3)&((alu5-(61*alu33))!=0))?(alu33+-1):alu33);
  int alu41 = (alu4+(alu40*-61));
  int alu42 = (((alu6<-3)&((alu7-(61*alu35))!=0))?(alu35+-1):alu35);
  int alu43 = (alu6+(alu42*-61));
  int alu44 = ((alu12<0)?(alu12+64):alu12);
  int alu45 = ((alu17<0)?(alu17+64):alu17);
  int alu46 = ((alu22<0)?(alu22+64):alu22);
  int alu47 = ((alu27<0)?(alu27+64):alu27);
  int alu48 = ((alu37<-3)?(alu37+64):(alu37+3));
  int alu49 = ((alu39<-3)?(alu39+64):(alu39+3));
  int alu50 = ((alu41<-3)?(alu41+64):(alu41+3));
  int alu51 = ((alu43<-3)?(alu43+64):(alu43+3));
  int alu52 = ((alu11<0)?(alu11+32):alu11);
  int alu53 = ((alu16<0)?(alu16+32):alu16);
  int alu54 = ((alu21<0)?(alu21+32):alu21);
  int alu55 = ((alu26<0)?(alu26+32):alu26);
  for (int Lidx4 = 0; Lidx4 < 78; Lidx4++) {
    _Bool alu56 = (Lidx4<62);
    float val4 = (alu56?*(data1_248+Lidx4):0.0f);
    _Bool alu57 = (61<Lidx4);
    float val5 = ((alu57&(-1<alu44)&(alu44<64))?*(data3_1024+((alu44<<4)+Lidx4+-62)):0.0f);
    float val6 = ((alu57&(-1<alu52)&(alu52<32))?*(data4_512+((alu52<<4)+Lidx4+-62)):0.0f);
    float val7 = ((alu57&(-1<alu48)&(alu48<61))?*(data5_976+((alu48<<4)+Lidx4+-62)):0.0f);
    float val8 = (alu56?*(data1_248+(Lidx4+62)):0.0f);
    float val9 = ((alu57&(-1<alu45)&(alu45<64))?*(data3_1024+((alu45<<4)+Lidx4+-62)):0.0f);
    float val10 = ((alu57&(-1<alu53)&(alu53<32))?*(data4_512+((alu53<<4)+Lidx4+-62)):0.0f);
    float val11 = ((alu57&(-1<alu49)&(alu49<61))?*(data5_976+((alu49<<4)+Lidx4+-62)):0.0f);
    float val12 = (alu56?*(data1_248+(Lidx4+124)):0.0f);
    float val13 = ((alu57&(-1<alu46)&(alu46<64))?*(data3_1024+((alu46<<4)+Lidx4+-62)):0.0f);
    float val14 = ((alu57&(-1<alu54)&(alu54<32))?*(data4_512+((alu54<<4)+Lidx4+-62)):0.0f);
    float val15 = ((alu57&(-1<alu50)&(alu50<61))?*(data5_976+((alu50<<4)+Lidx4+-62)):0.0f);
    float val16 = (alu56?*(data1_248+(Lidx4+186)):0.0f);
    float val17 = ((alu57&(-1<alu47)&(alu47<64))?*(data3_1024+((alu47<<4)+Lidx4+-62)):0.0f);
    float val18 = ((alu57&(-1<alu55)&(alu55<32))?*(data4_512+((alu55<<4)+Lidx4+-62)):0.0f);
    float val19 = ((alu57&(-1<alu51)&(alu51<61))?*(data5_976+((alu51<<4)+Lidx4+-62)):0.0f);
    float alu58 = (alu56?0.0f:(val9+val10+val11));
    float alu59 = (alu56?0.0f:(val5+val6+val7));
    float alu60 = (alu56?0.0f:(val13+val14+val15));
    float alu61 = (alu56?0.0f:(val17+val18+val19));
    *(data0_312+(Lidx4+78)) = (val8+alu58);
    *(data0_312+(Lidx4+156)) = (val12+alu60);
    *(data0_312+(Lidx4+234)) = (val16+alu61);
    *(data0_312+Lidx4) = (val4+alu59);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_E_16_4n1(float* restrict data0_64, int* restrict data1_1, float* restrict data2_576) {
  int val0 = (*(data1_1+0));
  int alu0 = ((val0<0)?(val0+9):val0);
  for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
    int alu1 = (Lidx1<<2);
    float4 val1 = (((-1<alu0)&(alu0<9))?*((float4*)((data2_576+((alu0<<6)+alu1)))):(float4){0.0f,0.0f,0.0f,0.0f});
    *((float4*)((data0_64+alu1))) = val1;
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4_78n1(float* restrict data0_256, float* restrict data1_312, float* restrict data2_4992, float* restrict data3_64, float* restrict data4_64) {
  float acc0[4];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 16; Lidx2++) {
      int alu0 = (Lidx2<<2);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 78; Ridx0++) {
        float val0 = (*(data1_312+((Lidx1*78)+Ridx0)));
        float4 val1 = (*((float4*)((data2_4992+((Ridx0<<6)+alu0)))));
        *(acc0+0) = ((*(acc0+0))+(val0*val1[0]));
        *(acc0+1) = ((*(acc0+1))+(val0*val1[1]));
        *(acc0+2) = ((*(acc0+2))+(val0*val1[2]));
        *(acc0+3) = ((*(acc0+3))+(val0*val1[3]));
      }
      float4 val2 = (*((float4*)((data3_64+alu0))));
      float4 val3 = (*((float4*)((data4_64+alu0))));
      *((float4*)((data0_256+((Lidx1<<6)+alu0)))) = (float4){((*(acc0+0))+val2[0]+val3[0]),((*(acc0+1))+val2[1]+val3[1]),((*(acc0+2))+val2[2]+val3[2]),((*(acc0+3))+val2[3]+val3[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4n2(float* restrict data0_4, float* restrict data1_256) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val0 = (*((float4*)((data1_256+((Ridx0<<2)+(Lidx1<<6))))));
      *(acc0+0) = ((*(acc0+0))+val0[0]+val0[1]+val0[2]+val0[3]);
    }
    *(data0_4+Lidx1) = ((*(acc0+0))*0.015625f);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4n3(float* restrict data0_4, float* restrict data1_256, float* restrict data2_4) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    float val0 = (*(data2_4+Lidx1));
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val1 = (*((float4*)((data1_256+((Ridx0<<2)+(Lidx1<<6))))));
      float alu1 = (val1[0]-val0);
      float alu2 = (val1[1]-val0);
      float alu3 = (val1[2]-val0);
      float alu4 = (val1[3]-val0);
      *(acc0+0) = ((*(acc0+0))+(alu1*alu1)+(alu2*alu2)+(alu3*alu3)+(alu4*alu4));
    }
    *(data0_4+Lidx1) = (1.0f/__builtin_sqrtf((((*(acc0+0))*0.015625f)+1e-05f)));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_E_4_16_4n1(float* restrict data0_256, float* restrict data1_256, float* restrict data2_4, float* restrict data3_4, float* restrict data4_64, float* restrict data5_64) {
  for (int Lidx0 = 0; Lidx0 < 4; Lidx0++) {
    float val0 = (*(data2_4+Lidx0));
    float val1 = (*(data3_4+Lidx0));
    for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
      int alu0 = (Lidx1<<2);
      int alu1 = ((Lidx0<<6)+alu0);
      float4 val2 = (*((float4*)((data1_256+alu1))));
      float4 val3 = (*((float4*)((data4_64+alu0))));
      float4 val4 = (*((float4*)((data5_64+alu0))));
      *((float4*)((data0_256+alu1))) = (float4){(((val2[0]-val0)*val1*val3[0])+val4[0]),(((val2[1]-val0)*val1*val3[1])+val4[1]),(((val2[2]-val0)*val1*val3[2])+val4[2]),(((val2[3]-val0)*val1*val3[3])+val4[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_64_16_4n1(float* restrict data0_256, float* restrict data1_256, float* restrict data2_4096, float* restrict data3_64) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    int alu0 = (Lidx1<<6);
    for (int Lidx2 = 0; Lidx2 < 64; Lidx2++) {
      *(acc0+0) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
        int alu2 = ((Ridx0<<8)+Lidx2);
        float val0 = (*(data2_4096+(alu2+64)));
        float val1 = (*(data2_4096+(alu2+128)));
        float val2 = (*(data2_4096+(alu2+192)));
        float val3 = (*(data2_4096+alu2));
        float4 val4 = (*((float4*)((data1_256+((Ridx0<<2)+alu0)))));
        *(acc0+0) = ((*(acc0+0))+(val4[0]*val3)+(val4[1]*val0)+(val4[2]*val1)+(val4[3]*val2));
      }
      float val5 = (*(data3_64+Lidx2));
      *(data0_256+(alu0+Lidx2)) = ((*(acc0+0))+val5);
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_4_26_16_64_16n1(float* restrict data0_416, float* restrict data1_256, float* restrict data2_1600, float* restrict data3_256, float* restrict data4_4096, float* restrict data5_64, float* restrict data6_24) {
  float acc0[16];
  float acc1[1];
  for (int Lidx3 = 0; Lidx3 < 4; Lidx3++) {
    int alu0 = (Lidx3<<4);
    float4 val0 = (*((float4*)((data5_64+(alu0+4)))));
    float4 val1 = (*((float4*)((data5_64+(alu0+8)))));
    float4 val2 = (*((float4*)((data5_64+(alu0+12)))));
    float4 val3 = (*((float4*)((data5_64+alu0))));
    for (int Lidx4 = 0; Lidx4 < 4; Lidx4++) {
      int alu1 = (Lidx4<<6);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      *(acc0+4) = 0.0f;
      *(acc0+5) = 0.0f;
      *(acc0+6) = 0.0f;
      *(acc0+7) = 0.0f;
      *(acc0+8) = 0.0f;
      *(acc0+9) = 0.0f;
      *(acc0+10) = 0.0f;
      *(acc0+11) = 0.0f;
      *(acc0+12) = 0.0f;
      *(acc0+13) = 0.0f;
      *(acc0+14) = 0.0f;
      *(acc0+15) = 0.0f;
      for (int Ridx1 = 0; Ridx1 < 64; Ridx1++) {
        float val4 = (*(data3_256+(alu1+Ridx1)));
        int alu18 = ((Ridx1<<6)+alu0);
        float4 val5 = (*((float4*)((data4_4096+(alu18+4)))));
        float4 val6 = (*((float4*)((data4_4096+(alu18+8)))));
        float4 val7 = (*((float4*)((data4_4096+(alu18+12)))));
        float4 val8 = (*((float4*)((data4_4096+alu18))));
        *(acc0+0) = ((*(acc0+0))+(val4*val8[0]));
        *(acc0+1) = ((*(acc0+1))+(val4*val8[1]));
        *(acc0+2) = ((*(acc0+2))+(val4*val8[2]));
        *(acc0+3) = ((*(acc0+3))+(val4*val8[3]));
        *(acc0+4) = ((*(acc0+4))+(val4*val5[0]));
        *(acc0+5) = ((*(acc0+5))+(val4*val5[1]));
        *(acc0+6) = ((*(acc0+6))+(val4*val5[2]));
        *(acc0+7) = ((*(acc0+7))+(val4*val5[3]));
        *(acc0+8) = ((*(acc0+8))+(val4*val6[0]));
        *(acc0+9) = ((*(acc0+9))+(val4*val6[1]));
        *(acc0+10) = ((*(acc0+10))+(val4*val6[2]));
        *(acc0+11) = ((*(acc0+11))+(val4*val6[3]));
        *(acc0+12) = ((*(acc0+12))+(val4*val7[0]));
        *(acc0+13) = ((*(acc0+13))+(val4*val7[1]));
        *(acc0+14) = ((*(acc0+14))+(val4*val7[2]));
        *(acc0+15) = ((*(acc0+15))+(val4*val7[3]));
      }
      int alu36 = (alu0+alu1);
      float4 val9 = (*((float4*)((data1_256+(alu36+4)))));
      float4 val10 = (*((float4*)((data1_256+(alu36+8)))));
      float4 val11 = (*((float4*)((data1_256+(alu36+12)))));
      float4 val12 = (*((float4*)((data1_256+alu36))));
      for (int Lidx5 = 0; Lidx5 < 26; Lidx5++) {
        _Bool alu37 = (Lidx5<25);
        *(acc1+0) = 0.0f;
        for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
          float val13 = (*(data1_256+(alu0+Ridx0+alu1)));
          float val14 = (alu37?*(data2_1600+((Lidx3*400)+(Lidx5<<4)+Ridx0)):0.0f);
          *(acc1+0) = ((*(acc1+0))+(val13*val14));
        }
        float val15 = (((0<Lidx5)&alu37)?*(data6_24+(Lidx5+-1)):0.0f);
        float alu41 = ((Lidx5<1)?1.0f:0.0f);
        float alu42 = (alu37?0.0f:1.0f);
        float alu43 = (alu37?(*(acc1+0)):0.0f);
        float alu44 = (alu37?0.0f:((val12[0]*((*(acc0+0))+val3[0]))+(val12[1]*((*(acc0+1))+val3[1]))+(val12[2]*((*(acc0+2))+val3[2]))+(val12[3]*((*(acc0+3))+val3[3]))+(val9[0]*((*(acc0+4))+val0[0]))+(val9[1]*((*(acc0+5))+val0[1]))+(val9[2]*((*(acc0+6))+val0[2]))+(val9[3]*((*(acc0+7))+val0[3]))+(val10[0]*((*(acc0+8))+val1[0]))+(val10[1]*((*(acc0+9))+val1[1]))+(val10[2]*((*(acc0+10))+val1[2]))+(val10[3]*((*(acc0+11))+val1[3]))+(val11[0]*((*(acc0+12))+val2[0]))+(val11[1]*((*(acc0+13))+val2[1]))+(val11[2]*((*(acc0+14))+val2[2]))+(val11[3]*((*(acc0+15))+val2[3]))));
        *(data0_416+((Lidx4*26)+Lidx5+(Lidx3*104))) = (((alu43+alu44)*0.25f)+((alu41+val15+alu42+-1.0f)*1000000000.0f));
      }
    }
  }
}

typedef float float2 __attribute__((aligned(8),ext_vector_type(2)));
void jepa_predict4_r_16_26n2(float* restrict data0_16, float* restrict data1_416) {
  for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
    int alu0 = (Lidx1*26);
    float2 val0 = (*((float2*)((data1_416+(alu0+2)))));
    float2 val1 = (*((float2*)((data1_416+(alu0+4)))));
    float2 val2 = (*((float2*)((data1_416+(alu0+6)))));
    float2 val3 = (*((float2*)((data1_416+(alu0+8)))));
    float2 val4 = (*((float2*)((data1_416+(alu0+10)))));
    float2 val5 = (*((float2*)((data1_416+(alu0+12)))));
    float2 val6 = (*((float2*)((data1_416+(alu0+14)))));
    float2 val7 = (*((float2*)((data1_416+(alu0+16)))));
    float2 val8 = (*((float2*)((data1_416+(alu0+18)))));
    float2 val9 = (*((float2*)((data1_416+(alu0+20)))));
    float2 val10 = (*((float2*)((data1_416+(alu0+22)))));
    float2 val11 = (*((float2*)((data1_416+(alu0+24)))));
    float2 val12 = (*((float2*)((data1_416+alu0))));
    float alu1 = ((val12[0]<val12[1])?val12[1]:val12[0]);
    float alu2 = ((alu1<val0[0])?val0[0]:alu1);
    float alu3 = ((alu2<val0[1])?val0[1]:alu2);
    float alu4 = ((alu3<val1[0])?val1[0]:alu3);
    float alu5 = ((alu4<val1[1])?val1[1]:alu4);
    float alu6 = ((alu5<val2[0])?val2[0]:alu5);
    float alu7 = ((alu6<val2[1])?val2[1]:alu6);
    float alu8 = ((alu7<val3[0])?val3[0]:alu7);
    float alu9 = ((alu8<val3[1])?val3[1]:alu8);
    float alu10 = ((alu9<val4[0])?val4[0]:alu9);
    float alu11 = ((alu10<val4[1])?val4[1]:alu10);
    float alu12 = ((alu11<val5[0])?val5[0]:alu11);
    float alu13 = ((alu12<val5[1])?val5[1]:alu12);
    float alu14 = ((alu13<val6[0])?val6[0]:alu13);
    float alu15 = ((alu14<val6[1])?val6[1]:alu14);
    float alu16 = ((alu15<val7[0])?val7[0]:alu15);
    float alu17 = ((alu16<val7[1])?val7[1]:alu16);
    float alu18 = ((alu17<val8[0])?val8[0]:alu17);
    float alu19 = ((alu18<val8[1])?val8[1]:alu18);
    float alu20 = ((alu19<val9[0])?val9[0]:alu19);
    float alu21 = ((alu20<val9[1])?val9[1]:alu20);
    float alu22 = ((alu21<val10[0])?val10[0]:alu21);
    float alu23 = ((alu22<val10[1])?val10[1]:alu22);
    float alu24 = ((alu23<val11[0])?val11[0]:alu23);
    float alu25 = ((alu24<val11[1])?val11[1]:alu24);
    *(data0_16+Lidx1) = alu25;
  }
}

typedef float float2 __attribute__((aligned(8),ext_vector_type(2)));
void jepa_predict4_r_16_26n3(float* restrict data0_16, float* restrict data1_416, float* restrict data2_16) {
  for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
    float val0 = (*(data2_16+Lidx1));
    int alu0 = (Lidx1*26);
    float2 val1 = (*((float2*)((data1_416+(alu0+2)))));
    float2 val2 = (*((float2*)((data1_416+(alu0+4)))));
    float2 val3 = (*((float2*)((data1_416+(alu0+6)))));
    float2 val4 = (*((float2*)((data1_416+(alu0+8)))));
    float2 val5 = (*((float2*)((data1_416+(alu0+10)))));
    float2 val6 = (*((float2*)((data1_416+(alu0+12)))));
    float2 val7 = (*((float2*)((data1_416+(alu0+14)))));
    float2 val8 = (*((float2*)((data1_416+(alu0+16)))));
    float2 val9 = (*((float2*)((data1_416+(alu0+18)))));
    float2 val10 = (*((float2*)((data1_416+(alu0+20)))));
    float2 val11 = (*((float2*)((data1_416+(alu0+22)))));
    float2 val12 = (*((float2*)((data1_416+(alu0+24)))));
    float2 val13 = (*((float2*)((data1_416+alu0))));
    float alu1 = ((val1[0]-val0)*1.4426950408889634f);
    _Bool alu2 = (alu1!=alu1);
    float alu3 = ((alu1!=((float)(-__builtin_inff())))?alu1:0.0f);
    float alu4 = (alu2?0.0f:alu3);
    float alu5 = ((alu1!=((float)(__builtin_inff())))?alu4:0.0f);
    float alu6 = ((alu5<0.0f)?-0.5f:0.5f);
    int cast0 = ((int)((alu5+alu6)));
    float alu7 = ((val2[0]-val0)*1.4426950408889634f);
    _Bool alu8 = (alu7!=alu7);
    float alu9 = ((alu7!=((float)(-__builtin_inff())))?alu7:0.0f);
    float alu10 = (alu8?0.0f:alu9);
    float alu11 = ((alu7!=((float)(__builtin_inff())))?alu10:0.0f);
    float alu12 = ((alu11<0.0f)?-0.5f:0.5f);
    int cast1 = ((int)((alu11+alu12)));
    float alu13 = ((val3[0]-val0)*1.4426950408889634f);
    _Bool alu14 = (alu13!=alu13);
    float alu15 = ((alu13!=((float)(-__builtin_inff())))?alu13:0.0f);
    float alu16 = (alu14?0.0f:alu15);
    float alu17 = ((alu13!=((float)(__builtin_inff())))?alu16:0.0f);
    float alu18 = ((alu17<0.0f)?-0.5f:0.5f);
    int cast2 = ((int)((alu17+alu18)));
    float alu19 = ((val4[0]-val0)*1.4426950408889634f);
    _Bool alu20 = (alu19!=alu19);
    float alu21 = ((alu19!=((float)(-__builtin_inff())))?alu19:0.0f);
    float alu22 = (alu20?0.0f:alu21);
    float alu23 = ((alu19!=((float)(__builtin_inff())))?alu22:0.0f);
    float alu24 = ((alu23<0.0f)?-0.5f:0.5f);
    int cast3 = ((int)((alu23+alu24)));
    float alu25 = ((val5[0]-val0)*1.4426950408889634f);
    _Bool alu26 = (alu25!=alu25);
    float alu27 = ((alu25!=((float)(-__builtin_inff())))?alu25:0.0f);
    float alu28 = (alu26?0.0f:alu27);
    float alu29 = ((alu25!=((float)(__builtin_inff())))?alu28:0.0f);
    float alu30 = ((alu29<0.0f)?-0.5f:0.5f);
    int cast4 = ((int)((alu29+alu30)));
    float alu31 = ((val6[0]-val0)*1.4426950408889634f);
    _Bool alu32 = (alu31!=alu31);
    float alu33 = ((alu31!=((float)(-__builtin_inff())))?alu31:0.0f);
    float alu34 = (alu32?0.0f:alu33);
    float alu35 = ((alu31!=((float)(__builtin_inff())))?alu34:0.0f);
    float alu36 = ((alu35<0.0f)?-0.5f:0.5f);
    int cast5 = ((int)((alu35+alu36)));
    float alu37 = ((val7[0]-val0)*1.4426950408889634f);
    _Bool alu38 = (alu37!=alu37);
    float alu39 = ((alu37!=((float)(-__builtin_inff())))?alu37:0.0f);
    float alu40 = (alu38?0.0f:alu39);
    float alu41 = ((alu37!=((float)(__builtin_inff())))?alu40:0.0f);
    float alu42 = ((alu41<0.0f)?-0.5f:0.5f);
    int cast6 = ((int)((alu41+alu42)));
    float alu43 = ((val8[0]-val0)*1.4426950408889634f);
    _Bool alu44 = (alu43!=alu43);
    float alu45 = ((alu43!=((float)(-__builtin_inff())))?alu43:0.0f);
    float alu46 = (alu44?0.0f:alu45);
    float alu47 = ((alu43!=((float)(__builtin_inff())))?alu46:0.0f);
    float alu48 = ((alu47<0.0f)?-0.5f:0.5f);
    int cast7 = ((int)((alu47+alu48)));
    float alu49 = ((val9[0]-val0)*1.4426950408889634f);
    _Bool alu50 = (alu49!=alu49);
    float alu51 = ((alu49!=((float)(-__builtin_inff())))?alu49:0.0f);
    float alu52 = (alu50?0.0f:alu51);
    float alu53 = ((alu49!=((float)(__builtin_inff())))?alu52:0.0f);
    float alu54 = ((alu53<0.0f)?-0.5f:0.5f);
    int cast8 = ((int)((alu53+alu54)));
    float alu55 = ((val10[0]-val0)*1.4426950408889634f);
    _Bool alu56 = (alu55!=alu55);
    float alu57 = ((alu55!=((float)(-__builtin_inff())))?alu55:0.0f);
    float alu58 = (alu56?0.0f:alu57);
    float alu59 = ((alu55!=((float)(__builtin_inff())))?alu58:0.0f);
    float alu60 = ((alu59<0.0f)?-0.5f:0.5f);
    int cast9 = ((int)((alu59+alu60)));
    float alu61 = ((val11[0]-val0)*1.4426950408889634f);
    _Bool alu62 = (alu61!=alu61);
    float alu63 = ((alu61!=((float)(-__builtin_inff())))?alu61:0.0f);
    float alu64 = (alu62?0.0f:alu63);
    float alu65 = ((alu61!=((float)(__builtin_inff())))?alu64:0.0f);
    float alu66 = ((alu65<0.0f)?-0.5f:0.5f);
    int cast10 = ((int)((alu65+alu66)));
    float alu67 = ((val12[0]-val0)*1.4426950408889634f);
    _Bool alu68 = (alu67!=alu67);
    float alu69 = ((alu67!=((float)(-__builtin_inff())))?alu67:0.0f);
    float alu70 = (alu68?0.0f:alu69);
    float alu71 = ((alu67!=((float)(__builtin_inff())))?alu70:0.0f);
    float alu72 = ((alu71<0.0f)?-0.5f:0.5f);
    int cast11 = ((int)((alu71+alu72)));
    float alu73 = ((val13[0]-val0)*1.4426950408889634f);
    _Bool alu74 = (alu73!=alu73);
    float alu75 = ((alu73!=((float)(-__builtin_inff())))?alu73:0.0f);
    float alu76 = (alu74?0.0f:alu75);
    float alu77 = ((alu73!=((float)(__builtin_inff())))?alu76:0.0f);
    float alu78 = ((alu77<0.0f)?-0.5f:0.5f);
    int cast12 = ((int)((alu77+alu78)));
    float alu79 = ((val1[1]-val0)*1.4426950408889634f);
    _Bool alu80 = (alu79!=alu79);
    float alu81 = ((alu79!=((float)(-__builtin_inff())))?alu79:0.0f);
    float alu82 = (alu80?0.0f:alu81);
    float alu83 = ((alu79!=((float)(__builtin_inff())))?alu82:0.0f);
    float alu84 = ((alu83<0.0f)?-0.5f:0.5f);
    int cast13 = ((int)((alu83+alu84)));
    float alu85 = ((val2[1]-val0)*1.4426950408889634f);
    _Bool alu86 = (alu85!=alu85);
    float alu87 = ((alu85!=((float)(-__builtin_inff())))?alu85:0.0f);
    float alu88 = (alu86?0.0f:alu87);
    float alu89 = ((alu85!=((float)(__builtin_inff())))?alu88:0.0f);
    float alu90 = ((alu89<0.0f)?-0.5f:0.5f);
    int cast14 = ((int)((alu89+alu90)));
    float alu91 = ((val3[1]-val0)*1.4426950408889634f);
    _Bool alu92 = (alu91!=alu91);
    float alu93 = ((alu91!=((float)(-__builtin_inff())))?alu91:0.0f);
    float alu94 = (alu92?0.0f:alu93);
    float alu95 = ((alu91!=((float)(__builtin_inff())))?alu94:0.0f);
    float alu96 = ((alu95<0.0f)?-0.5f:0.5f);
    int cast15 = ((int)((alu95+alu96)));
    float alu97 = ((val4[1]-val0)*1.4426950408889634f);
    _Bool alu98 = (alu97!=alu97);
    float alu99 = ((alu97!=((float)(-__builtin_inff())))?alu97:0.0f);
    float alu100 = (alu98?0.0f:alu99);
    float alu101 = ((alu97!=((float)(__builtin_inff())))?alu100:0.0f);
    float alu102 = ((alu101<0.0f)?-0.5f:0.5f);
    int cast16 = ((int)((alu101+alu102)));
    float alu103 = ((val5[1]-val0)*1.4426950408889634f);
    _Bool alu104 = (alu103!=alu103);
    float alu105 = ((alu103!=((float)(-__builtin_inff())))?alu103:0.0f);
    float alu106 = (alu104?0.0f:alu105);
    float alu107 = ((alu103!=((float)(__builtin_inff())))?alu106:0.0f);
    float alu108 = ((alu107<0.0f)?-0.5f:0.5f);
    int cast17 = ((int)((alu107+alu108)));
    float alu109 = ((val6[1]-val0)*1.4426950408889634f);
    _Bool alu110 = (alu109!=alu109);
    float alu111 = ((alu109!=((float)(-__builtin_inff())))?alu109:0.0f);
    float alu112 = (alu110?0.0f:alu111);
    float alu113 = ((alu109!=((float)(__builtin_inff())))?alu112:0.0f);
    float alu114 = ((alu113<0.0f)?-0.5f:0.5f);
    int cast18 = ((int)((alu113+alu114)));
    float alu115 = ((val7[1]-val0)*1.4426950408889634f);
    _Bool alu116 = (alu115!=alu115);
    float alu117 = ((alu115!=((float)(-__builtin_inff())))?alu115:0.0f);
    float alu118 = (alu116?0.0f:alu117);
    float alu119 = ((alu115!=((float)(__builtin_inff())))?alu118:0.0f);
    float alu120 = ((alu119<0.0f)?-0.5f:0.5f);
    int cast19 = ((int)((alu119+alu120)));
    float alu121 = ((val8[1]-val0)*1.4426950408889634f);
    _Bool alu122 = (alu121!=alu121);
    float alu123 = ((alu121!=((float)(-__builtin_inff())))?alu121:0.0f);
    float alu124 = (alu122?0.0f:alu123);
    float alu125 = ((alu121!=((float)(__builtin_inff())))?alu124:0.0f);
    float alu126 = ((alu125<0.0f)?-0.5f:0.5f);
    int cast20 = ((int)((alu125+alu126)));
    float alu127 = ((val9[1]-val0)*1.4426950408889634f);
    _Bool alu128 = (alu127!=alu127);
    float alu129 = ((alu127!=((float)(-__builtin_inff())))?alu127:0.0f);
    float alu130 = (alu128?0.0f:alu129);
    float alu131 = ((alu127!=((float)(__builtin_inff())))?alu130:0.0f);
    float alu132 = ((alu131<0.0f)?-0.5f:0.5f);
    int cast21 = ((int)((alu131+alu132)));
    float alu133 = ((val10[1]-val0)*1.4426950408889634f);
    _Bool alu134 = (alu133!=alu133);
    float alu135 = ((alu133!=((float)(-__builtin_inff())))?alu133:0.0f);
    float alu136 = (alu134?0.0f:alu135);
    float alu137 = ((alu133!=((float)(__builtin_inff())))?alu136:0.0f);
    float alu138 = ((alu137<0.0f)?-0.5f:0.5f);
    int cast22 = ((int)((alu137+alu138)));
    float alu139 = ((val11[1]-val0)*1.4426950408889634f);
    _Bool alu140 = (alu139!=alu139);
    float alu141 = ((alu139!=((float)(-__builtin_inff())))?alu139:0.0f);
    float alu142 = (alu140?0.0f:alu141);
    float alu143 = ((alu139!=((float)(__builtin_inff())))?alu142:0.0f);
    float alu144 = ((alu143<0.0f)?-0.5f:0.5f);
    int cast23 = ((int)((alu143+alu144)));
    float alu145 = ((val12[1]-val0)*1.4426950408889634f);
    _Bool alu146 = (alu145!=alu145);
    float alu147 = ((alu145!=((float)(-__builtin_inff())))?alu145:0.0f);
    float alu148 = (alu146?0.0f:alu147);
    float alu149 = ((alu145!=((float)(__builtin_inff())))?alu148:0.0f);
    float alu150 = ((alu149<0.0f)?-0.5f:0.5f);
    int cast24 = ((int)((alu149+alu150)));
    float alu151 = ((val13[1]-val0)*1.4426950408889634f);
    _Bool alu152 = (alu151!=alu151);
    float alu153 = ((alu151!=((float)(-__builtin_inff())))?alu151:0.0f);
    float alu154 = (alu152?0.0f:alu153);
    float alu155 = ((alu151!=((float)(__builtin_inff())))?alu154:0.0f);
    float alu156 = ((alu155<0.0f)?-0.5f:0.5f);
    int cast25 = ((int)((alu155+alu156)));
    int alu157 = ((cast0<0)?1:0);
    int alu158 = ((cast0+alu157)>>1);
    int alu159 = ((cast1<0)?1:0);
    int alu160 = ((cast1+alu159)>>1);
    int alu161 = ((cast2<0)?1:0);
    int alu162 = ((cast2+alu161)>>1);
    int alu163 = ((cast3<0)?1:0);
    int alu164 = ((cast3+alu163)>>1);
    int alu165 = ((cast4<0)?1:0);
    int alu166 = ((cast4+alu165)>>1);
    int alu167 = ((cast5<0)?1:0);
    int alu168 = ((cast5+alu167)>>1);
    int alu169 = ((cast6<0)?1:0);
    int alu170 = ((cast6+alu169)>>1);
    int alu171 = ((cast7<0)?1:0);
    int alu172 = ((cast7+alu171)>>1);
    int alu173 = ((cast8<0)?1:0);
    int alu174 = ((cast8+alu173)>>1);
    int alu175 = ((cast9<0)?1:0);
    int alu176 = ((cast9+alu175)>>1);
    int alu177 = ((cast10<0)?1:0);
    int alu178 = ((cast10+alu177)>>1);
    int alu179 = ((cast11<0)?1:0);
    int alu180 = ((cast11+alu179)>>1);
    int alu181 = ((cast12<0)?1:0);
    int alu182 = ((cast12+alu181)>>1);
    int alu183 = ((cast13<0)?1:0);
    int alu184 = ((cast13+alu183)>>1);
    int alu185 = ((cast14<0)?1:0);
    int alu186 = ((cast14+alu185)>>1);
    int alu187 = ((cast15<0)?1:0);
    int alu188 = ((cast15+alu187)>>1);
    int alu189 = ((cast16<0)?1:0);
    int alu190 = ((cast16+alu189)>>1);
    int alu191 = ((cast17<0)?1:0);
    int alu192 = ((cast17+alu191)>>1);
    int alu193 = ((cast18<0)?1:0);
    int alu194 = ((cast18+alu193)>>1);
    int alu195 = ((cast19<0)?1:0);
    int alu196 = ((cast19+alu195)>>1);
    int alu197 = ((cast20<0)?1:0);
    int alu198 = ((cast20+alu197)>>1);
    int alu199 = ((cast21<0)?1:0);
    int alu200 = ((cast21+alu199)>>1);
    int alu201 = ((cast22<0)?1:0);
    int alu202 = ((cast22+alu201)>>1);
    int alu203 = ((cast23<0)?1:0);
    int alu204 = ((cast23+alu203)>>1);
    int alu205 = ((cast24<0)?1:0);
    int alu206 = ((cast24+alu205)>>1);
    int alu207 = ((cast25<0)?1:0);
    int alu208 = ((cast25+alu207)>>1);
    float alu209 = (alu5-((float)(cast0)));
    float alu210 = (alu77-((float)(cast12)));
    float alu211 = (alu155-((float)(cast25)));
    float alu212 = (((alu73<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu210)+0.001339262701f)*alu210)+0.009618384764f)*alu210)+0.05550347269f)*alu210)+0.2402264476f)*alu210)+0.6931471825f)*alu210)+1.0f)*__builtin_bit_cast(float, (int)(((alu182+127)<<23)))*__builtin_bit_cast(float, (int)((((cast12-alu182)+127)<<23)))));
    float alu213 = ((alu73<-150.0f)?0.0f:alu212);
    float alu214 = (((alu151<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu211)+0.001339262701f)*alu211)+0.009618384764f)*alu211)+0.05550347269f)*alu211)+0.2402264476f)*alu211)+0.6931471825f)*alu211)+1.0f)*__builtin_bit_cast(float, (int)(((alu208+127)<<23)))*__builtin_bit_cast(float, (int)((((cast25-alu208)+127)<<23)))));
    float alu215 = ((alu151<-150.0f)?0.0f:alu214);
    float alu216 = (alu74?((float)(__builtin_nanf(""))):alu213);
    float alu217 = (alu152?((float)(__builtin_nanf(""))):alu215);
    float alu218 = (((alu1<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu209)+0.001339262701f)*alu209)+0.009618384764f)*alu209)+0.05550347269f)*alu209)+0.2402264476f)*alu209)+0.6931471825f)*alu209)+1.0f)*__builtin_bit_cast(float, (int)(((alu158+127)<<23)))*__builtin_bit_cast(float, (int)((((cast0-alu158)+127)<<23)))));
    float alu219 = ((alu1<-150.0f)?0.0f:alu218);
    float alu220 = (alu2?((float)(__builtin_nanf(""))):alu219);
    float alu221 = (alu83-((float)(cast13)));
    float alu222 = (((alu79<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu221)+0.001339262701f)*alu221)+0.009618384764f)*alu221)+0.05550347269f)*alu221)+0.2402264476f)*alu221)+0.6931471825f)*alu221)+1.0f)*__builtin_bit_cast(float, (int)(((alu184+127)<<23)))*__builtin_bit_cast(float, (int)((((cast13-alu184)+127)<<23)))));
    float alu223 = ((alu79<-150.0f)?0.0f:alu222);
    float alu224 = (alu80?((float)(__builtin_nanf(""))):alu223);
    float alu225 = (alu11-((float)(cast1)));
    float alu226 = (((alu7<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu225)+0.001339262701f)*alu225)+0.009618384764f)*alu225)+0.05550347269f)*alu225)+0.2402264476f)*alu225)+0.6931471825f)*alu225)+1.0f)*__builtin_bit_cast(float, (int)(((alu160+127)<<23)))*__builtin_bit_cast(float, (int)((((cast1-alu160)+127)<<23)))));
    float alu227 = ((alu7<-150.0f)?0.0f:alu226);
    float alu228 = (alu8?((float)(__builtin_nanf(""))):alu227);
    float alu229 = (alu89-((float)(cast14)));
    float alu230 = (((alu85<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu229)+0.001339262701f)*alu229)+0.009618384764f)*alu229)+0.05550347269f)*alu229)+0.2402264476f)*alu229)+0.6931471825f)*alu229)+1.0f)*__builtin_bit_cast(float, (int)(((alu186+127)<<23)))*__builtin_bit_cast(float, (int)((((cast14-alu186)+127)<<23)))));
    float alu231 = ((alu85<-150.0f)?0.0f:alu230);
    float alu232 = (alu86?((float)(__builtin_nanf(""))):alu231);
    float alu233 = (alu17-((float)(cast2)));
    float alu234 = (((alu13<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu233)+0.001339262701f)*alu233)+0.009618384764f)*alu233)+0.05550347269f)*alu233)+0.2402264476f)*alu233)+0.6931471825f)*alu233)+1.0f)*__builtin_bit_cast(float, (int)(((alu162+127)<<23)))*__builtin_bit_cast(float, (int)((((cast2-alu162)+127)<<23)))));
    float alu235 = ((alu13<-150.0f)?0.0f:alu234);
    float alu236 = (alu14?((float)(__builtin_nanf(""))):alu235);
    float alu237 = (alu95-((float)(cast15)));
    float alu238 = (((alu91<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu237)+0.001339262701f)*alu237)+0.009618384764f)*alu237)+0.05550347269f)*alu237)+0.2402264476f)*alu237)+0.6931471825f)*alu237)+1.0f)*__builtin_bit_cast(float, (int)(((alu188+127)<<23)))*__builtin_bit_cast(float, (int)((((cast15-alu188)+127)<<23)))));
    float alu239 = ((alu91<-150.0f)?0.0f:alu238);
    float alu240 = (alu92?((float)(__builtin_nanf(""))):alu239);
    float alu241 = (alu23-((float)(cast3)));
    float alu242 = (((alu19<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu241)+0.001339262701f)*alu241)+0.009618384764f)*alu241)+0.05550347269f)*alu241)+0.2402264476f)*alu241)+0.6931471825f)*alu241)+1.0f)*__builtin_bit_cast(float, (int)(((alu164+127)<<23)))*__builtin_bit_cast(float, (int)((((cast3-alu164)+127)<<23)))));
    float alu243 = ((alu19<-150.0f)?0.0f:alu242);
    float alu244 = (alu20?((float)(__builtin_nanf(""))):alu243);
    float alu245 = (alu101-((float)(cast16)));
    float alu246 = (((alu97<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu245)+0.001339262701f)*alu245)+0.009618384764f)*alu245)+0.05550347269f)*alu245)+0.2402264476f)*alu245)+0.6931471825f)*alu245)+1.0f)*__builtin_bit_cast(float, (int)(((alu190+127)<<23)))*__builtin_bit_cast(float, (int)((((cast16-alu190)+127)<<23)))));
    float alu247 = ((alu97<-150.0f)?0.0f:alu246);
    float alu248 = (alu98?((float)(__builtin_nanf(""))):alu247);
    float alu249 = (alu29-((float)(cast4)));
    float alu250 = (((alu25<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu249)+0.001339262701f)*alu249)+0.009618384764f)*alu249)+0.05550347269f)*alu249)+0.2402264476f)*alu249)+0.6931471825f)*alu249)+1.0f)*__builtin_bit_cast(float, (int)(((alu166+127)<<23)))*__builtin_bit_cast(float, (int)((((cast4-alu166)+127)<<23)))));
    float alu251 = ((alu25<-150.0f)?0.0f:alu250);
    float alu252 = (alu26?((float)(__builtin_nanf(""))):alu251);
    float alu253 = (alu107-((float)(cast17)));
    float alu254 = (((alu103<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu253)+0.001339262701f)*alu253)+0.009618384764f)*alu253)+0.05550347269f)*alu253)+0.2402264476f)*alu253)+0.6931471825f)*alu253)+1.0f)*__builtin_bit_cast(float, (int)(((alu192+127)<<23)))*__builtin_bit_cast(float, (int)((((cast17-alu192)+127)<<23)))));
    float alu255 = ((alu103<-150.0f)?0.0f:alu254);
    float alu256 = (alu104?((float)(__builtin_nanf(""))):alu255);
    float alu257 = (alu35-((float)(cast5)));
    float alu258 = (((alu31<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu257)+0.001339262701f)*alu257)+0.009618384764f)*alu257)+0.05550347269f)*alu257)+0.2402264476f)*alu257)+0.6931471825f)*alu257)+1.0f)*__builtin_bit_cast(float, (int)(((alu168+127)<<23)))*__builtin_bit_cast(float, (int)((((cast5-alu168)+127)<<23)))));
    float alu259 = ((alu31<-150.0f)?0.0f:alu258);
    float alu260 = (alu32?((float)(__builtin_nanf(""))):alu259);
    float alu261 = (alu113-((float)(cast18)));
    float alu262 = (((alu109<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu261)+0.001339262701f)*alu261)+0.009618384764f)*alu261)+0.05550347269f)*alu261)+0.2402264476f)*alu261)+0.6931471825f)*alu261)+1.0f)*__builtin_bit_cast(float, (int)(((alu194+127)<<23)))*__builtin_bit_cast(float, (int)((((cast18-alu194)+127)<<23)))));
    float alu263 = ((alu109<-150.0f)?0.0f:alu262);
    float alu264 = (alu110?((float)(__builtin_nanf(""))):alu263);
    float alu265 = (alu41-((float)(cast6)));
    float alu266 = (((alu37<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu265)+0.001339262701f)*alu265)+0.009618384764f)*alu265)+0.05550347269f)*alu265)+0.2402264476f)*alu265)+0.6931471825f)*alu265)+1.0f)*__builtin_bit_cast(float, (int)(((alu170+127)<<23)))*__builtin_bit_cast(float, (int)((((cast6-alu170)+127)<<23)))));
    float alu267 = ((alu37<-150.0f)?0.0f:alu266);
    float alu268 = (alu38?((float)(__builtin_nanf(""))):alu267);
    float alu269 = (alu119-((float)(cast19)));
    float alu270 = (((alu115<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu269)+0.001339262701f)*alu269)+0.009618384764f)*alu269)+0.05550347269f)*alu269)+0.2402264476f)*alu269)+0.6931471825f)*alu269)+1.0f)*__builtin_bit_cast(float, (int)(((alu196+127)<<23)))*__builtin_bit_cast(float, (int)((((cast19-alu196)+127)<<23)))));
    float alu271 = ((alu115<-150.0f)?0.0f:alu270);
    float alu272 = (alu116?((float)(__builtin_nanf(""))):alu271);
    float alu273 = (alu47-((float)(cast7)));
    float alu274 = (((alu43<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu273)+0.001339262701f)*alu273)+0.009618384764f)*alu273)+0.05550347269f)*alu273)+0.2402264476f)*alu273)+0.6931471825f)*alu273)+1.0f)*__builtin_bit_cast(float, (int)(((alu172+127)<<23)))*__builtin_bit_cast(float, (int)((((cast7-alu172)+127)<<23)))));
    float alu275 = ((alu43<-150.0f)?0.0f:alu274);
    float alu276 = (alu44?((float)(__builtin_nanf(""))):alu275);
    float alu277 = (alu125-((float)(cast20)));
    float alu278 = (((alu121<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu277)+0.001339262701f)*alu277)+0.009618384764f)*alu277)+0.05550347269f)*alu277)+0.2402264476f)*alu277)+0.6931471825f)*alu277)+1.0f)*__builtin_bit_cast(float, (int)(((alu198+127)<<23)))*__builtin_bit_cast(float, (int)((((cast20-alu198)+127)<<23)))));
    float alu279 = ((alu121<-150.0f)?0.0f:alu278);
    float alu280 = (alu122?((float)(__builtin_nanf(""))):alu279);
    float alu281 = (alu53-((float)(cast8)));
    float alu282 = (((alu49<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu281)+0.001339262701f)*alu281)+0.009618384764f)*alu281)+0.05550347269f)*alu281)+0.2402264476f)*alu281)+0.6931471825f)*alu281)+1.0f)*__builtin_bit_cast(float, (int)(((alu174+127)<<23)))*__builtin_bit_cast(float, (int)((((cast8-alu174)+127)<<23)))));
    float alu283 = ((alu49<-150.0f)?0.0f:alu282);
    float alu284 = (alu50?((float)(__builtin_nanf(""))):alu283);
    float alu285 = (alu131-((float)(cast21)));
    float alu286 = (((alu127<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu285)+0.001339262701f)*alu285)+0.009618384764f)*alu285)+0.05550347269f)*alu285)+0.2402264476f)*alu285)+0.6931471825f)*alu285)+1.0f)*__builtin_bit_cast(float, (int)(((alu200+127)<<23)))*__builtin_bit_cast(float, (int)((((cast21-alu200)+127)<<23)))));
    float alu287 = ((alu127<-150.0f)?0.0f:alu286);
    float alu288 = (alu128?((float)(__builtin_nanf(""))):alu287);
    float alu289 = (alu59-((float)(cast9)));
    float alu290 = (((alu55<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu289)+0.001339262701f)*alu289)+0.009618384764f)*alu289)+0.05550347269f)*alu289)+0.2402264476f)*alu289)+0.6931471825f)*alu289)+1.0f)*__builtin_bit_cast(float, (int)(((alu176+127)<<23)))*__builtin_bit_cast(float, (int)((((cast9-alu176)+127)<<23)))));
    float alu291 = ((alu55<-150.0f)?0.0f:alu290);
    float alu292 = (alu56?((float)(__builtin_nanf(""))):alu291);
    float alu293 = (alu137-((float)(cast22)));
    float alu294 = (((alu133<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu293)+0.001339262701f)*alu293)+0.009618384764f)*alu293)+0.05550347269f)*alu293)+0.2402264476f)*alu293)+0.6931471825f)*alu293)+1.0f)*__builtin_bit_cast(float, (int)(((alu202+127)<<23)))*__builtin_bit_cast(float, (int)((((cast22-alu202)+127)<<23)))));
    float alu295 = ((alu133<-150.0f)?0.0f:alu294);
    float alu296 = (alu134?((float)(__builtin_nanf(""))):alu295);
    float alu297 = (alu65-((float)(cast10)));
    float alu298 = (((alu61<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu297)+0.001339262701f)*alu297)+0.009618384764f)*alu297)+0.05550347269f)*alu297)+0.2402264476f)*alu297)+0.6931471825f)*alu297)+1.0f)*__builtin_bit_cast(float, (int)(((alu178+127)<<23)))*__builtin_bit_cast(float, (int)((((cast10-alu178)+127)<<23)))));
    float alu299 = ((alu61<-150.0f)?0.0f:alu298);
    float alu300 = (alu62?((float)(__builtin_nanf(""))):alu299);
    float alu301 = (alu143-((float)(cast23)));
    float alu302 = (((alu139<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu301)+0.001339262701f)*alu301)+0.009618384764f)*alu301)+0.05550347269f)*alu301)+0.2402264476f)*alu301)+0.6931471825f)*alu301)+1.0f)*__builtin_bit_cast(float, (int)(((alu204+127)<<23)))*__builtin_bit_cast(float, (int)((((cast23-alu204)+127)<<23)))));
    float alu303 = ((alu139<-150.0f)?0.0f:alu302);
    float alu304 = (alu140?((float)(__builtin_nanf(""))):alu303);
    float alu305 = (alu71-((float)(cast11)));
    float alu306 = (((alu67<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu305)+0.001339262701f)*alu305)+0.009618384764f)*alu305)+0.05550347269f)*alu305)+0.2402264476f)*alu305)+0.6931471825f)*alu305)+1.0f)*__builtin_bit_cast(float, (int)(((alu180+127)<<23)))*__builtin_bit_cast(float, (int)((((cast11-alu180)+127)<<23)))));
    float alu307 = ((alu67<-150.0f)?0.0f:alu306);
    float alu308 = (alu68?((float)(__builtin_nanf(""))):alu307);
    float alu309 = (alu149-((float)(cast24)));
    float alu310 = (((alu145<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu309)+0.001339262701f)*alu309)+0.009618384764f)*alu309)+0.05550347269f)*alu309)+0.2402264476f)*alu309)+0.6931471825f)*alu309)+1.0f)*__builtin_bit_cast(float, (int)(((alu206+127)<<23)))*__builtin_bit_cast(float, (int)((((cast24-alu206)+127)<<23)))));
    float alu311 = ((alu145<-150.0f)?0.0f:alu310);
    float alu312 = (alu146?((float)(__builtin_nanf(""))):alu311);
    *(data0_16+Lidx1) = (1.0f/(alu216+alu217+alu220+alu224+alu228+alu232+alu236+alu240+alu244+alu248+alu252+alu256+alu260+alu264+alu268+alu272+alu276+alu280+alu284+alu288+alu292+alu296+alu300+alu304+alu308+alu312));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_4_16_25_16_4n1(float* restrict data0_256, float* restrict data1_416, float* restrict data2_16, float* restrict data3_16, float* restrict data4_1600, float* restrict data5_256, float* restrict data6_4096, float* restrict data7_64) {
  float acc0[1];
  float acc1[1];
  for (int Lidx2 = 0; Lidx2 < 4; Lidx2++) {
    int alu0 = (Lidx2*104);
    for (int Lidx3 = 0; Lidx3 < 4; Lidx3++) {
      int alu1 = ((Lidx2<<2)+Lidx3);
      float val0 = (*(data2_16+alu1));
      float val1 = (*(data3_16+alu1));
      int alu2 = (Lidx3*26);
      float val2 = (*(data1_416+(alu0+alu2+25)));
      float alu3 = ((val2-val0)*1.4426950408889634f);
      _Bool alu4 = (alu3!=alu3);
      float alu5 = ((alu3!=((float)(-__builtin_inff())))?alu3:0.0f);
      float alu6 = (alu4?0.0f:alu5);
      float alu7 = ((alu3!=((float)(__builtin_inff())))?alu6:0.0f);
      float alu8 = ((alu7<0.0f)?-0.5f:0.5f);
      int cast0 = ((int)((alu7+alu8)));
      int alu9 = ((cast0<0)?1:0);
      int alu10 = ((cast0+alu9)>>1);
      float alu11 = (alu7-((float)(cast0)));
      float alu12 = (((alu3<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu11)+0.001339262701f)*alu11)+0.009618384764f)*alu11)+0.05550347269f)*alu11)+0.2402264476f)*alu11)+0.6931471825f)*alu11)+1.0f)*__builtin_bit_cast(float, (int)(((alu10+127)<<23)))*__builtin_bit_cast(float, (int)((((cast0-alu10)+127)<<23)))));
      float alu13 = ((alu3<-150.0f)?0.0f:alu12);
      float alu14 = (alu4?((float)(__builtin_nanf(""))):alu13);
      for (int Lidx4 = 0; Lidx4 < 16; Lidx4++) {
        *(acc1+0) = 0.0f;
        for (int Ridx0 = 0; Ridx0 < 25; Ridx0++) {
          float val3 = (*(data1_416+(alu2+Ridx0+alu0)));
          float val4 = (*(data4_1600+((Ridx0<<4)+Lidx4+(Lidx2*400))));
          float alu16 = ((val3-val0)*1.4426950408889634f);
          _Bool alu17 = (alu16!=alu16);
          float alu18 = ((alu16!=((float)(-__builtin_inff())))?alu16:0.0f);
          float alu19 = (alu17?0.0f:alu18);
          float alu20 = ((alu16!=((float)(__builtin_inff())))?alu19:0.0f);
          float alu21 = ((alu20<0.0f)?-0.5f:0.5f);
          int cast1 = ((int)((alu20+alu21)));
          int alu22 = ((cast1<0)?1:0);
          int alu23 = ((cast1+alu22)>>1);
          float alu24 = (alu20-((float)(cast1)));
          float alu25 = (((alu16<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu24)+0.001339262701f)*alu24)+0.009618384764f)*alu24)+0.05550347269f)*alu24)+0.2402264476f)*alu24)+0.6931471825f)*alu24)+1.0f)*__builtin_bit_cast(float, (int)(((alu23+127)<<23)))*__builtin_bit_cast(float, (int)((((cast1-alu23)+127)<<23)))));
          float alu26 = ((alu16<-150.0f)?0.0f:alu25);
          float alu27 = (alu17?((float)(__builtin_nanf(""))):alu26);
          *(acc1+0) = ((*(acc1+0))+(alu27*val4));
        }
        int alu30 = ((Lidx2<<4)+Lidx4);
        *(acc0+0) = 0.0f;
        for (int Ridx1 = 0; Ridx1 < 16; Ridx1++) {
          int alu32 = (alu30+(Ridx1<<8));
          float val5 = (*(data6_4096+(alu32+64)));
          float val6 = (*(data6_4096+(alu32+128)));
          float val7 = (*(data6_4096+(alu32+192)));
          float val8 = (*(data6_4096+alu32));
          float4 val9 = (*((float4*)((data5_256+((Ridx1<<2)+(Lidx3<<6))))));
          *(acc0+0) = ((*(acc0+0))+(val9[0]*val8)+(val9[1]*val5)+(val9[2]*val6)+(val9[3]*val7));
        }
        float val10 = (*(data7_64+alu30));
        *(data0_256+((Lidx3<<4)+Lidx4+(Lidx2<<6))) = (((*(acc1+0))*val1)+(alu14*val1*((*(acc0+0))+val10)));
      }
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_64_4_16n1(float* restrict data0_256, float* restrict data1_256, float* restrict data2_256, float* restrict data3_4096, float* restrict data4_64) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 64; Lidx2++) {
      *(acc0+0) = 0.0f;
      for (int Ridx0_0 = 0; Ridx0_0 < 4; Ridx0_0++) {
        int alu1 = ((Ridx0_0<<10)+Lidx2);
        float val0 = (*(data3_4096+(alu1+64)));
        float val1 = (*(data3_4096+(alu1+128)));
        float val2 = (*(data3_4096+(alu1+192)));
        float val3 = (*(data3_4096+(alu1+256)));
        float val4 = (*(data3_4096+(alu1+320)));
        float val5 = (*(data3_4096+(alu1+384)));
        float val6 = (*(data3_4096+(alu1+448)));
        float val7 = (*(data3_4096+(alu1+512)));
        float val8 = (*(data3_4096+(alu1+576)));
        float val9 = (*(data3_4096+(alu1+640)));
        float val10 = (*(data3_4096+(alu1+704)));
        float val11 = (*(data3_4096+(alu1+768)));
        float val12 = (*(data3_4096+(alu1+832)));
        float val13 = (*(data3_4096+(alu1+896)));
        float val14 = (*(data3_4096+(alu1+960)));
        float val15 = (*(data3_4096+alu1));
        int alu2 = ((Ridx0_0<<6)+(Lidx1<<4));
        float4 val16 = (*((float4*)((data2_256+(alu2+4)))));
        float4 val17 = (*((float4*)((data2_256+(alu2+8)))));
        float4 val18 = (*((float4*)((data2_256+(alu2+12)))));
        float4 val19 = (*((float4*)((data2_256+alu2))));
        *(acc0+0) = ((*(acc0+0))+(val19[0]*val15)+(val19[1]*val0)+(val19[2]*val1)+(val19[3]*val2)+(val16[0]*val3)+(val16[1]*val4)+(val16[2]*val5)+(val16[3]*val6)+(val17[0]*val7)+(val17[1]*val8)+(val17[2]*val9)+(val17[3]*val10)+(val18[0]*val11)+(val18[1]*val12)+(val18[2]*val13)+(val18[3]*val14));
      }
      int alu5 = ((Lidx1<<6)+Lidx2);
      float val20 = (*(data1_256+alu5));
      float val21 = (*(data4_64+Lidx2));
      *(data0_256+alu5) = (val20+(*(acc0+0))+val21);
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4n4(float* restrict data0_4, float* restrict data1_256) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val0 = (*((float4*)((data1_256+((Ridx0<<2)+(Lidx1<<6))))));
      *(acc0+0) = ((*(acc0+0))+val0[0]+val0[1]+val0[2]+val0[3]);
    }
    *(data0_4+Lidx1) = ((*(acc0+0))*0.015625f);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4n5(float* restrict data0_4, float* restrict data1_256, float* restrict data2_4) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    float val0 = (*(data2_4+Lidx1));
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val1 = (*((float4*)((data1_256+((Ridx0<<2)+(Lidx1<<6))))));
      float alu1 = (val1[0]-val0);
      float alu2 = (val1[1]-val0);
      float alu3 = (val1[2]-val0);
      float alu4 = (val1[3]-val0);
      *(acc0+0) = ((*(acc0+0))+(alu1*alu1)+(alu2*alu2)+(alu3*alu3)+(alu4*alu4));
    }
    *(data0_4+Lidx1) = (1.0f/__builtin_sqrtf((((*(acc0+0))*0.015625f)+1e-05f)));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_E_4_16_4n2(float* restrict data0_256, float* restrict data1_256, float* restrict data2_4, float* restrict data3_4, float* restrict data4_64, float* restrict data5_64) {
  for (int Lidx0 = 0; Lidx0 < 4; Lidx0++) {
    float val0 = (*(data2_4+Lidx0));
    float val1 = (*(data3_4+Lidx0));
    for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
      int alu0 = (Lidx1<<2);
      int alu1 = ((Lidx0<<6)+alu0);
      float4 val2 = (*((float4*)((data1_256+alu1))));
      float4 val3 = (*((float4*)((data4_64+alu0))));
      float4 val4 = (*((float4*)((data5_64+alu0))));
      *((float4*)((data0_256+alu1))) = (float4){(((val2[0]-val0)*val1*val3[0])+val4[0]),(((val2[1]-val0)*val1*val3[1])+val4[1]),(((val2[2]-val0)*val1*val3[2])+val4[2]),(((val2[3]-val0)*val1*val3[3])+val4[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_128_4_16_4n1(float* restrict data0_512, float* restrict data1_256, float* restrict data2_8192, float* restrict data3_128) {
  float acc0[4];
  for (int Lidx2 = 0; Lidx2 < 128; Lidx2++) {
    *(acc0+0) = 0.0f;
    *(acc0+1) = 0.0f;
    *(acc0+2) = 0.0f;
    *(acc0+3) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      int alu4 = ((Ridx0<<9)+Lidx2);
      float val0 = (*(data2_8192+(alu4+128)));
      float val1 = (*(data2_8192+(alu4+256)));
      float val2 = (*(data2_8192+(alu4+384)));
      float val3 = (*(data2_8192+alu4));
      int alu5 = (Ridx0<<2);
      float4 val4 = (*((float4*)((data1_256+(alu5+64)))));
      float4 val5 = (*((float4*)((data1_256+(alu5+128)))));
      float4 val6 = (*((float4*)((data1_256+(alu5+192)))));
      float4 val7 = (*((float4*)((data1_256+alu5))));
      *(acc0+0) = ((*(acc0+0))+(val7[0]*val3)+(val7[1]*val0)+(val7[2]*val1)+(val7[3]*val2));
      *(acc0+1) = ((*(acc0+1))+(val4[0]*val3)+(val4[1]*val0)+(val4[2]*val1)+(val4[3]*val2));
      *(acc0+2) = ((*(acc0+2))+(val5[0]*val3)+(val5[1]*val0)+(val5[2]*val1)+(val5[3]*val2));
      *(acc0+3) = ((*(acc0+3))+(val6[0]*val3)+(val6[1]*val0)+(val6[2]*val1)+(val6[3]*val2));
    }
    float val8 = (*(data3_128+Lidx2));
    float alu11 = ((*(acc0+0))+val8);
    float alu12 = ((*(acc0+1))+val8);
    float alu13 = ((*(acc0+2))+val8);
    float alu14 = ((*(acc0+3))+val8);
    float alu15 = ((0.0f<alu11)?alu11:0.0f);
    float alu16 = ((0.0f<alu12)?alu12:0.0f);
    float alu17 = ((0.0f<alu13)?alu13:0.0f);
    float alu18 = ((0.0f<alu14)?alu14:0.0f);
    *(data0_512+(Lidx2+128)) = alu16;
    *(data0_512+(Lidx2+256)) = alu17;
    *(data0_512+(Lidx2+384)) = alu18;
    *(data0_512+Lidx2) = alu15;
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_64_32_4n1(float* restrict data0_256, float* restrict data1_256, float* restrict data2_512, float* restrict data3_8192, float* restrict data4_64) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 64; Lidx2++) {
      *(acc0+0) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 32; Ridx0++) {
        int alu1 = ((Ridx0<<8)+Lidx2);
        float val0 = (*(data3_8192+(alu1+64)));
        float val1 = (*(data3_8192+(alu1+128)));
        float val2 = (*(data3_8192+(alu1+192)));
        float val3 = (*(data3_8192+alu1));
        float4 val4 = (*((float4*)((data2_512+((Ridx0<<2)+(Lidx1<<7))))));
        *(acc0+0) = ((*(acc0+0))+(val4[0]*val3)+(val4[1]*val0)+(val4[2]*val1)+(val4[3]*val2));
      }
      int alu4 = ((Lidx1<<6)+Lidx2);
      float val5 = (*(data1_256+alu4));
      float val6 = (*(data4_64+Lidx2));
      *(data0_256+alu4) = (val5+(*(acc0+0))+val6);
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4n6(float* restrict data0_4, float* restrict data1_256) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val0 = (*((float4*)((data1_256+((Ridx0<<2)+(Lidx1<<6))))));
      *(acc0+0) = ((*(acc0+0))+val0[0]+val0[1]+val0[2]+val0[3]);
    }
    *(data0_4+Lidx1) = ((*(acc0+0))*0.015625f);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4n7(float* restrict data0_4, float* restrict data1_256, float* restrict data2_4) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    float val0 = (*(data2_4+Lidx1));
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val1 = (*((float4*)((data1_256+((Ridx0<<2)+(Lidx1<<6))))));
      float alu1 = (val1[0]-val0);
      float alu2 = (val1[1]-val0);
      float alu3 = (val1[2]-val0);
      float alu4 = (val1[3]-val0);
      *(acc0+0) = ((*(acc0+0))+(alu1*alu1)+(alu2*alu2)+(alu3*alu3)+(alu4*alu4));
    }
    *(data0_4+Lidx1) = (1.0f/__builtin_sqrtf((((*(acc0+0))*0.015625f)+1e-05f)));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_E_4_16_4n3(float* restrict data0_256, float* restrict data1_256, float* restrict data2_4, float* restrict data3_4, float* restrict data4_64, float* restrict data5_64) {
  for (int Lidx0 = 0; Lidx0 < 4; Lidx0++) {
    float val0 = (*(data2_4+Lidx0));
    float val1 = (*(data3_4+Lidx0));
    for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
      int alu0 = (Lidx1<<2);
      int alu1 = ((Lidx0<<6)+alu0);
      float4 val2 = (*((float4*)((data1_256+alu1))));
      float4 val3 = (*((float4*)((data4_64+alu0))));
      float4 val4 = (*((float4*)((data5_64+alu0))));
      *((float4*)((data0_256+alu1))) = (float4){(((val2[0]-val0)*val1*val3[0])+val4[0]),(((val2[1]-val0)*val1*val3[1])+val4[1]),(((val2[2]-val0)*val1*val3[2])+val4[2]),(((val2[3]-val0)*val1*val3[3])+val4[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_64_16_4n2(float* restrict data0_256, float* restrict data1_256, float* restrict data2_4096, float* restrict data3_64) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    int alu0 = (Lidx1<<6);
    for (int Lidx2 = 0; Lidx2 < 64; Lidx2++) {
      *(acc0+0) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
        int alu2 = ((Ridx0<<8)+Lidx2);
        float val0 = (*(data2_4096+(alu2+64)));
        float val1 = (*(data2_4096+(alu2+128)));
        float val2 = (*(data2_4096+(alu2+192)));
        float val3 = (*(data2_4096+alu2));
        float4 val4 = (*((float4*)((data1_256+((Ridx0<<2)+alu0)))));
        *(acc0+0) = ((*(acc0+0))+(val4[0]*val3)+(val4[1]*val0)+(val4[2]*val1)+(val4[3]*val2));
      }
      float val5 = (*(data3_64+Lidx2));
      *(data0_256+(alu0+Lidx2)) = ((*(acc0+0))+val5);
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_4_26_16_64_16n2(float* restrict data0_416, float* restrict data1_256, float* restrict data2_1600, float* restrict data3_256, float* restrict data4_4096, float* restrict data5_64, float* restrict data6_24) {
  float acc0[16];
  float acc1[1];
  for (int Lidx3 = 0; Lidx3 < 4; Lidx3++) {
    int alu0 = (Lidx3<<4);
    float4 val0 = (*((float4*)((data5_64+(alu0+4)))));
    float4 val1 = (*((float4*)((data5_64+(alu0+8)))));
    float4 val2 = (*((float4*)((data5_64+(alu0+12)))));
    float4 val3 = (*((float4*)((data5_64+alu0))));
    for (int Lidx4 = 0; Lidx4 < 4; Lidx4++) {
      int alu1 = (Lidx4<<6);
      *(acc0+0) = 0.0f;
      *(acc0+1) = 0.0f;
      *(acc0+2) = 0.0f;
      *(acc0+3) = 0.0f;
      *(acc0+4) = 0.0f;
      *(acc0+5) = 0.0f;
      *(acc0+6) = 0.0f;
      *(acc0+7) = 0.0f;
      *(acc0+8) = 0.0f;
      *(acc0+9) = 0.0f;
      *(acc0+10) = 0.0f;
      *(acc0+11) = 0.0f;
      *(acc0+12) = 0.0f;
      *(acc0+13) = 0.0f;
      *(acc0+14) = 0.0f;
      *(acc0+15) = 0.0f;
      for (int Ridx1 = 0; Ridx1 < 64; Ridx1++) {
        float val4 = (*(data3_256+(alu1+Ridx1)));
        int alu18 = ((Ridx1<<6)+alu0);
        float4 val5 = (*((float4*)((data4_4096+(alu18+4)))));
        float4 val6 = (*((float4*)((data4_4096+(alu18+8)))));
        float4 val7 = (*((float4*)((data4_4096+(alu18+12)))));
        float4 val8 = (*((float4*)((data4_4096+alu18))));
        *(acc0+0) = ((*(acc0+0))+(val4*val8[0]));
        *(acc0+1) = ((*(acc0+1))+(val4*val8[1]));
        *(acc0+2) = ((*(acc0+2))+(val4*val8[2]));
        *(acc0+3) = ((*(acc0+3))+(val4*val8[3]));
        *(acc0+4) = ((*(acc0+4))+(val4*val5[0]));
        *(acc0+5) = ((*(acc0+5))+(val4*val5[1]));
        *(acc0+6) = ((*(acc0+6))+(val4*val5[2]));
        *(acc0+7) = ((*(acc0+7))+(val4*val5[3]));
        *(acc0+8) = ((*(acc0+8))+(val4*val6[0]));
        *(acc0+9) = ((*(acc0+9))+(val4*val6[1]));
        *(acc0+10) = ((*(acc0+10))+(val4*val6[2]));
        *(acc0+11) = ((*(acc0+11))+(val4*val6[3]));
        *(acc0+12) = ((*(acc0+12))+(val4*val7[0]));
        *(acc0+13) = ((*(acc0+13))+(val4*val7[1]));
        *(acc0+14) = ((*(acc0+14))+(val4*val7[2]));
        *(acc0+15) = ((*(acc0+15))+(val4*val7[3]));
      }
      int alu36 = (alu0+alu1);
      float4 val9 = (*((float4*)((data1_256+(alu36+4)))));
      float4 val10 = (*((float4*)((data1_256+(alu36+8)))));
      float4 val11 = (*((float4*)((data1_256+(alu36+12)))));
      float4 val12 = (*((float4*)((data1_256+alu36))));
      for (int Lidx5 = 0; Lidx5 < 26; Lidx5++) {
        _Bool alu37 = (Lidx5<25);
        *(acc1+0) = 0.0f;
        for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
          float val13 = (*(data1_256+(alu0+Ridx0+alu1)));
          float val14 = (alu37?*(data2_1600+((Lidx3*400)+(Lidx5<<4)+Ridx0)):0.0f);
          *(acc1+0) = ((*(acc1+0))+(val13*val14));
        }
        float val15 = (((0<Lidx5)&alu37)?*(data6_24+(Lidx5+-1)):0.0f);
        float alu41 = ((Lidx5<1)?1.0f:0.0f);
        float alu42 = (alu37?0.0f:1.0f);
        float alu43 = (alu37?(*(acc1+0)):0.0f);
        float alu44 = (alu37?0.0f:((val12[0]*((*(acc0+0))+val3[0]))+(val12[1]*((*(acc0+1))+val3[1]))+(val12[2]*((*(acc0+2))+val3[2]))+(val12[3]*((*(acc0+3))+val3[3]))+(val9[0]*((*(acc0+4))+val0[0]))+(val9[1]*((*(acc0+5))+val0[1]))+(val9[2]*((*(acc0+6))+val0[2]))+(val9[3]*((*(acc0+7))+val0[3]))+(val10[0]*((*(acc0+8))+val1[0]))+(val10[1]*((*(acc0+9))+val1[1]))+(val10[2]*((*(acc0+10))+val1[2]))+(val10[3]*((*(acc0+11))+val1[3]))+(val11[0]*((*(acc0+12))+val2[0]))+(val11[1]*((*(acc0+13))+val2[1]))+(val11[2]*((*(acc0+14))+val2[2]))+(val11[3]*((*(acc0+15))+val2[3]))));
        *(data0_416+((Lidx4*26)+Lidx5+(Lidx3*104))) = (((alu43+alu44)*0.25f)+((alu41+val15+alu42+-1.0f)*1000000000.0f));
      }
    }
  }
}

typedef float float2 __attribute__((aligned(8),ext_vector_type(2)));
void jepa_predict4_r_16_26n4(float* restrict data0_16, float* restrict data1_416) {
  for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
    int alu0 = (Lidx1*26);
    float2 val0 = (*((float2*)((data1_416+(alu0+2)))));
    float2 val1 = (*((float2*)((data1_416+(alu0+4)))));
    float2 val2 = (*((float2*)((data1_416+(alu0+6)))));
    float2 val3 = (*((float2*)((data1_416+(alu0+8)))));
    float2 val4 = (*((float2*)((data1_416+(alu0+10)))));
    float2 val5 = (*((float2*)((data1_416+(alu0+12)))));
    float2 val6 = (*((float2*)((data1_416+(alu0+14)))));
    float2 val7 = (*((float2*)((data1_416+(alu0+16)))));
    float2 val8 = (*((float2*)((data1_416+(alu0+18)))));
    float2 val9 = (*((float2*)((data1_416+(alu0+20)))));
    float2 val10 = (*((float2*)((data1_416+(alu0+22)))));
    float2 val11 = (*((float2*)((data1_416+(alu0+24)))));
    float2 val12 = (*((float2*)((data1_416+alu0))));
    float alu1 = ((val12[0]<val12[1])?val12[1]:val12[0]);
    float alu2 = ((alu1<val0[0])?val0[0]:alu1);
    float alu3 = ((alu2<val0[1])?val0[1]:alu2);
    float alu4 = ((alu3<val1[0])?val1[0]:alu3);
    float alu5 = ((alu4<val1[1])?val1[1]:alu4);
    float alu6 = ((alu5<val2[0])?val2[0]:alu5);
    float alu7 = ((alu6<val2[1])?val2[1]:alu6);
    float alu8 = ((alu7<val3[0])?val3[0]:alu7);
    float alu9 = ((alu8<val3[1])?val3[1]:alu8);
    float alu10 = ((alu9<val4[0])?val4[0]:alu9);
    float alu11 = ((alu10<val4[1])?val4[1]:alu10);
    float alu12 = ((alu11<val5[0])?val5[0]:alu11);
    float alu13 = ((alu12<val5[1])?val5[1]:alu12);
    float alu14 = ((alu13<val6[0])?val6[0]:alu13);
    float alu15 = ((alu14<val6[1])?val6[1]:alu14);
    float alu16 = ((alu15<val7[0])?val7[0]:alu15);
    float alu17 = ((alu16<val7[1])?val7[1]:alu16);
    float alu18 = ((alu17<val8[0])?val8[0]:alu17);
    float alu19 = ((alu18<val8[1])?val8[1]:alu18);
    float alu20 = ((alu19<val9[0])?val9[0]:alu19);
    float alu21 = ((alu20<val9[1])?val9[1]:alu20);
    float alu22 = ((alu21<val10[0])?val10[0]:alu21);
    float alu23 = ((alu22<val10[1])?val10[1]:alu22);
    float alu24 = ((alu23<val11[0])?val11[0]:alu23);
    float alu25 = ((alu24<val11[1])?val11[1]:alu24);
    *(data0_16+Lidx1) = alu25;
  }
}

typedef float float2 __attribute__((aligned(8),ext_vector_type(2)));
void jepa_predict4_r_16_26n5(float* restrict data0_16, float* restrict data1_416, float* restrict data2_16) {
  for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
    float val0 = (*(data2_16+Lidx1));
    int alu0 = (Lidx1*26);
    float2 val1 = (*((float2*)((data1_416+(alu0+2)))));
    float2 val2 = (*((float2*)((data1_416+(alu0+4)))));
    float2 val3 = (*((float2*)((data1_416+(alu0+6)))));
    float2 val4 = (*((float2*)((data1_416+(alu0+8)))));
    float2 val5 = (*((float2*)((data1_416+(alu0+10)))));
    float2 val6 = (*((float2*)((data1_416+(alu0+12)))));
    float2 val7 = (*((float2*)((data1_416+(alu0+14)))));
    float2 val8 = (*((float2*)((data1_416+(alu0+16)))));
    float2 val9 = (*((float2*)((data1_416+(alu0+18)))));
    float2 val10 = (*((float2*)((data1_416+(alu0+20)))));
    float2 val11 = (*((float2*)((data1_416+(alu0+22)))));
    float2 val12 = (*((float2*)((data1_416+(alu0+24)))));
    float2 val13 = (*((float2*)((data1_416+alu0))));
    float alu1 = ((val1[0]-val0)*1.4426950408889634f);
    _Bool alu2 = (alu1!=alu1);
    float alu3 = ((alu1!=((float)(-__builtin_inff())))?alu1:0.0f);
    float alu4 = (alu2?0.0f:alu3);
    float alu5 = ((alu1!=((float)(__builtin_inff())))?alu4:0.0f);
    float alu6 = ((alu5<0.0f)?-0.5f:0.5f);
    int cast0 = ((int)((alu5+alu6)));
    float alu7 = ((val2[0]-val0)*1.4426950408889634f);
    _Bool alu8 = (alu7!=alu7);
    float alu9 = ((alu7!=((float)(-__builtin_inff())))?alu7:0.0f);
    float alu10 = (alu8?0.0f:alu9);
    float alu11 = ((alu7!=((float)(__builtin_inff())))?alu10:0.0f);
    float alu12 = ((alu11<0.0f)?-0.5f:0.5f);
    int cast1 = ((int)((alu11+alu12)));
    float alu13 = ((val3[0]-val0)*1.4426950408889634f);
    _Bool alu14 = (alu13!=alu13);
    float alu15 = ((alu13!=((float)(-__builtin_inff())))?alu13:0.0f);
    float alu16 = (alu14?0.0f:alu15);
    float alu17 = ((alu13!=((float)(__builtin_inff())))?alu16:0.0f);
    float alu18 = ((alu17<0.0f)?-0.5f:0.5f);
    int cast2 = ((int)((alu17+alu18)));
    float alu19 = ((val4[0]-val0)*1.4426950408889634f);
    _Bool alu20 = (alu19!=alu19);
    float alu21 = ((alu19!=((float)(-__builtin_inff())))?alu19:0.0f);
    float alu22 = (alu20?0.0f:alu21);
    float alu23 = ((alu19!=((float)(__builtin_inff())))?alu22:0.0f);
    float alu24 = ((alu23<0.0f)?-0.5f:0.5f);
    int cast3 = ((int)((alu23+alu24)));
    float alu25 = ((val5[0]-val0)*1.4426950408889634f);
    _Bool alu26 = (alu25!=alu25);
    float alu27 = ((alu25!=((float)(-__builtin_inff())))?alu25:0.0f);
    float alu28 = (alu26?0.0f:alu27);
    float alu29 = ((alu25!=((float)(__builtin_inff())))?alu28:0.0f);
    float alu30 = ((alu29<0.0f)?-0.5f:0.5f);
    int cast4 = ((int)((alu29+alu30)));
    float alu31 = ((val6[0]-val0)*1.4426950408889634f);
    _Bool alu32 = (alu31!=alu31);
    float alu33 = ((alu31!=((float)(-__builtin_inff())))?alu31:0.0f);
    float alu34 = (alu32?0.0f:alu33);
    float alu35 = ((alu31!=((float)(__builtin_inff())))?alu34:0.0f);
    float alu36 = ((alu35<0.0f)?-0.5f:0.5f);
    int cast5 = ((int)((alu35+alu36)));
    float alu37 = ((val7[0]-val0)*1.4426950408889634f);
    _Bool alu38 = (alu37!=alu37);
    float alu39 = ((alu37!=((float)(-__builtin_inff())))?alu37:0.0f);
    float alu40 = (alu38?0.0f:alu39);
    float alu41 = ((alu37!=((float)(__builtin_inff())))?alu40:0.0f);
    float alu42 = ((alu41<0.0f)?-0.5f:0.5f);
    int cast6 = ((int)((alu41+alu42)));
    float alu43 = ((val8[0]-val0)*1.4426950408889634f);
    _Bool alu44 = (alu43!=alu43);
    float alu45 = ((alu43!=((float)(-__builtin_inff())))?alu43:0.0f);
    float alu46 = (alu44?0.0f:alu45);
    float alu47 = ((alu43!=((float)(__builtin_inff())))?alu46:0.0f);
    float alu48 = ((alu47<0.0f)?-0.5f:0.5f);
    int cast7 = ((int)((alu47+alu48)));
    float alu49 = ((val9[0]-val0)*1.4426950408889634f);
    _Bool alu50 = (alu49!=alu49);
    float alu51 = ((alu49!=((float)(-__builtin_inff())))?alu49:0.0f);
    float alu52 = (alu50?0.0f:alu51);
    float alu53 = ((alu49!=((float)(__builtin_inff())))?alu52:0.0f);
    float alu54 = ((alu53<0.0f)?-0.5f:0.5f);
    int cast8 = ((int)((alu53+alu54)));
    float alu55 = ((val10[0]-val0)*1.4426950408889634f);
    _Bool alu56 = (alu55!=alu55);
    float alu57 = ((alu55!=((float)(-__builtin_inff())))?alu55:0.0f);
    float alu58 = (alu56?0.0f:alu57);
    float alu59 = ((alu55!=((float)(__builtin_inff())))?alu58:0.0f);
    float alu60 = ((alu59<0.0f)?-0.5f:0.5f);
    int cast9 = ((int)((alu59+alu60)));
    float alu61 = ((val11[0]-val0)*1.4426950408889634f);
    _Bool alu62 = (alu61!=alu61);
    float alu63 = ((alu61!=((float)(-__builtin_inff())))?alu61:0.0f);
    float alu64 = (alu62?0.0f:alu63);
    float alu65 = ((alu61!=((float)(__builtin_inff())))?alu64:0.0f);
    float alu66 = ((alu65<0.0f)?-0.5f:0.5f);
    int cast10 = ((int)((alu65+alu66)));
    float alu67 = ((val12[0]-val0)*1.4426950408889634f);
    _Bool alu68 = (alu67!=alu67);
    float alu69 = ((alu67!=((float)(-__builtin_inff())))?alu67:0.0f);
    float alu70 = (alu68?0.0f:alu69);
    float alu71 = ((alu67!=((float)(__builtin_inff())))?alu70:0.0f);
    float alu72 = ((alu71<0.0f)?-0.5f:0.5f);
    int cast11 = ((int)((alu71+alu72)));
    float alu73 = ((val13[0]-val0)*1.4426950408889634f);
    _Bool alu74 = (alu73!=alu73);
    float alu75 = ((alu73!=((float)(-__builtin_inff())))?alu73:0.0f);
    float alu76 = (alu74?0.0f:alu75);
    float alu77 = ((alu73!=((float)(__builtin_inff())))?alu76:0.0f);
    float alu78 = ((alu77<0.0f)?-0.5f:0.5f);
    int cast12 = ((int)((alu77+alu78)));
    float alu79 = ((val1[1]-val0)*1.4426950408889634f);
    _Bool alu80 = (alu79!=alu79);
    float alu81 = ((alu79!=((float)(-__builtin_inff())))?alu79:0.0f);
    float alu82 = (alu80?0.0f:alu81);
    float alu83 = ((alu79!=((float)(__builtin_inff())))?alu82:0.0f);
    float alu84 = ((alu83<0.0f)?-0.5f:0.5f);
    int cast13 = ((int)((alu83+alu84)));
    float alu85 = ((val2[1]-val0)*1.4426950408889634f);
    _Bool alu86 = (alu85!=alu85);
    float alu87 = ((alu85!=((float)(-__builtin_inff())))?alu85:0.0f);
    float alu88 = (alu86?0.0f:alu87);
    float alu89 = ((alu85!=((float)(__builtin_inff())))?alu88:0.0f);
    float alu90 = ((alu89<0.0f)?-0.5f:0.5f);
    int cast14 = ((int)((alu89+alu90)));
    float alu91 = ((val3[1]-val0)*1.4426950408889634f);
    _Bool alu92 = (alu91!=alu91);
    float alu93 = ((alu91!=((float)(-__builtin_inff())))?alu91:0.0f);
    float alu94 = (alu92?0.0f:alu93);
    float alu95 = ((alu91!=((float)(__builtin_inff())))?alu94:0.0f);
    float alu96 = ((alu95<0.0f)?-0.5f:0.5f);
    int cast15 = ((int)((alu95+alu96)));
    float alu97 = ((val4[1]-val0)*1.4426950408889634f);
    _Bool alu98 = (alu97!=alu97);
    float alu99 = ((alu97!=((float)(-__builtin_inff())))?alu97:0.0f);
    float alu100 = (alu98?0.0f:alu99);
    float alu101 = ((alu97!=((float)(__builtin_inff())))?alu100:0.0f);
    float alu102 = ((alu101<0.0f)?-0.5f:0.5f);
    int cast16 = ((int)((alu101+alu102)));
    float alu103 = ((val5[1]-val0)*1.4426950408889634f);
    _Bool alu104 = (alu103!=alu103);
    float alu105 = ((alu103!=((float)(-__builtin_inff())))?alu103:0.0f);
    float alu106 = (alu104?0.0f:alu105);
    float alu107 = ((alu103!=((float)(__builtin_inff())))?alu106:0.0f);
    float alu108 = ((alu107<0.0f)?-0.5f:0.5f);
    int cast17 = ((int)((alu107+alu108)));
    float alu109 = ((val6[1]-val0)*1.4426950408889634f);
    _Bool alu110 = (alu109!=alu109);
    float alu111 = ((alu109!=((float)(-__builtin_inff())))?alu109:0.0f);
    float alu112 = (alu110?0.0f:alu111);
    float alu113 = ((alu109!=((float)(__builtin_inff())))?alu112:0.0f);
    float alu114 = ((alu113<0.0f)?-0.5f:0.5f);
    int cast18 = ((int)((alu113+alu114)));
    float alu115 = ((val7[1]-val0)*1.4426950408889634f);
    _Bool alu116 = (alu115!=alu115);
    float alu117 = ((alu115!=((float)(-__builtin_inff())))?alu115:0.0f);
    float alu118 = (alu116?0.0f:alu117);
    float alu119 = ((alu115!=((float)(__builtin_inff())))?alu118:0.0f);
    float alu120 = ((alu119<0.0f)?-0.5f:0.5f);
    int cast19 = ((int)((alu119+alu120)));
    float alu121 = ((val8[1]-val0)*1.4426950408889634f);
    _Bool alu122 = (alu121!=alu121);
    float alu123 = ((alu121!=((float)(-__builtin_inff())))?alu121:0.0f);
    float alu124 = (alu122?0.0f:alu123);
    float alu125 = ((alu121!=((float)(__builtin_inff())))?alu124:0.0f);
    float alu126 = ((alu125<0.0f)?-0.5f:0.5f);
    int cast20 = ((int)((alu125+alu126)));
    float alu127 = ((val9[1]-val0)*1.4426950408889634f);
    _Bool alu128 = (alu127!=alu127);
    float alu129 = ((alu127!=((float)(-__builtin_inff())))?alu127:0.0f);
    float alu130 = (alu128?0.0f:alu129);
    float alu131 = ((alu127!=((float)(__builtin_inff())))?alu130:0.0f);
    float alu132 = ((alu131<0.0f)?-0.5f:0.5f);
    int cast21 = ((int)((alu131+alu132)));
    float alu133 = ((val10[1]-val0)*1.4426950408889634f);
    _Bool alu134 = (alu133!=alu133);
    float alu135 = ((alu133!=((float)(-__builtin_inff())))?alu133:0.0f);
    float alu136 = (alu134?0.0f:alu135);
    float alu137 = ((alu133!=((float)(__builtin_inff())))?alu136:0.0f);
    float alu138 = ((alu137<0.0f)?-0.5f:0.5f);
    int cast22 = ((int)((alu137+alu138)));
    float alu139 = ((val11[1]-val0)*1.4426950408889634f);
    _Bool alu140 = (alu139!=alu139);
    float alu141 = ((alu139!=((float)(-__builtin_inff())))?alu139:0.0f);
    float alu142 = (alu140?0.0f:alu141);
    float alu143 = ((alu139!=((float)(__builtin_inff())))?alu142:0.0f);
    float alu144 = ((alu143<0.0f)?-0.5f:0.5f);
    int cast23 = ((int)((alu143+alu144)));
    float alu145 = ((val12[1]-val0)*1.4426950408889634f);
    _Bool alu146 = (alu145!=alu145);
    float alu147 = ((alu145!=((float)(-__builtin_inff())))?alu145:0.0f);
    float alu148 = (alu146?0.0f:alu147);
    float alu149 = ((alu145!=((float)(__builtin_inff())))?alu148:0.0f);
    float alu150 = ((alu149<0.0f)?-0.5f:0.5f);
    int cast24 = ((int)((alu149+alu150)));
    float alu151 = ((val13[1]-val0)*1.4426950408889634f);
    _Bool alu152 = (alu151!=alu151);
    float alu153 = ((alu151!=((float)(-__builtin_inff())))?alu151:0.0f);
    float alu154 = (alu152?0.0f:alu153);
    float alu155 = ((alu151!=((float)(__builtin_inff())))?alu154:0.0f);
    float alu156 = ((alu155<0.0f)?-0.5f:0.5f);
    int cast25 = ((int)((alu155+alu156)));
    int alu157 = ((cast0<0)?1:0);
    int alu158 = ((cast0+alu157)>>1);
    int alu159 = ((cast1<0)?1:0);
    int alu160 = ((cast1+alu159)>>1);
    int alu161 = ((cast2<0)?1:0);
    int alu162 = ((cast2+alu161)>>1);
    int alu163 = ((cast3<0)?1:0);
    int alu164 = ((cast3+alu163)>>1);
    int alu165 = ((cast4<0)?1:0);
    int alu166 = ((cast4+alu165)>>1);
    int alu167 = ((cast5<0)?1:0);
    int alu168 = ((cast5+alu167)>>1);
    int alu169 = ((cast6<0)?1:0);
    int alu170 = ((cast6+alu169)>>1);
    int alu171 = ((cast7<0)?1:0);
    int alu172 = ((cast7+alu171)>>1);
    int alu173 = ((cast8<0)?1:0);
    int alu174 = ((cast8+alu173)>>1);
    int alu175 = ((cast9<0)?1:0);
    int alu176 = ((cast9+alu175)>>1);
    int alu177 = ((cast10<0)?1:0);
    int alu178 = ((cast10+alu177)>>1);
    int alu179 = ((cast11<0)?1:0);
    int alu180 = ((cast11+alu179)>>1);
    int alu181 = ((cast12<0)?1:0);
    int alu182 = ((cast12+alu181)>>1);
    int alu183 = ((cast13<0)?1:0);
    int alu184 = ((cast13+alu183)>>1);
    int alu185 = ((cast14<0)?1:0);
    int alu186 = ((cast14+alu185)>>1);
    int alu187 = ((cast15<0)?1:0);
    int alu188 = ((cast15+alu187)>>1);
    int alu189 = ((cast16<0)?1:0);
    int alu190 = ((cast16+alu189)>>1);
    int alu191 = ((cast17<0)?1:0);
    int alu192 = ((cast17+alu191)>>1);
    int alu193 = ((cast18<0)?1:0);
    int alu194 = ((cast18+alu193)>>1);
    int alu195 = ((cast19<0)?1:0);
    int alu196 = ((cast19+alu195)>>1);
    int alu197 = ((cast20<0)?1:0);
    int alu198 = ((cast20+alu197)>>1);
    int alu199 = ((cast21<0)?1:0);
    int alu200 = ((cast21+alu199)>>1);
    int alu201 = ((cast22<0)?1:0);
    int alu202 = ((cast22+alu201)>>1);
    int alu203 = ((cast23<0)?1:0);
    int alu204 = ((cast23+alu203)>>1);
    int alu205 = ((cast24<0)?1:0);
    int alu206 = ((cast24+alu205)>>1);
    int alu207 = ((cast25<0)?1:0);
    int alu208 = ((cast25+alu207)>>1);
    float alu209 = (alu5-((float)(cast0)));
    float alu210 = (alu77-((float)(cast12)));
    float alu211 = (alu155-((float)(cast25)));
    float alu212 = (((alu73<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu210)+0.001339262701f)*alu210)+0.009618384764f)*alu210)+0.05550347269f)*alu210)+0.2402264476f)*alu210)+0.6931471825f)*alu210)+1.0f)*__builtin_bit_cast(float, (int)(((alu182+127)<<23)))*__builtin_bit_cast(float, (int)((((cast12-alu182)+127)<<23)))));
    float alu213 = ((alu73<-150.0f)?0.0f:alu212);
    float alu214 = (((alu151<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu211)+0.001339262701f)*alu211)+0.009618384764f)*alu211)+0.05550347269f)*alu211)+0.2402264476f)*alu211)+0.6931471825f)*alu211)+1.0f)*__builtin_bit_cast(float, (int)(((alu208+127)<<23)))*__builtin_bit_cast(float, (int)((((cast25-alu208)+127)<<23)))));
    float alu215 = ((alu151<-150.0f)?0.0f:alu214);
    float alu216 = (alu74?((float)(__builtin_nanf(""))):alu213);
    float alu217 = (alu152?((float)(__builtin_nanf(""))):alu215);
    float alu218 = (((alu1<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu209)+0.001339262701f)*alu209)+0.009618384764f)*alu209)+0.05550347269f)*alu209)+0.2402264476f)*alu209)+0.6931471825f)*alu209)+1.0f)*__builtin_bit_cast(float, (int)(((alu158+127)<<23)))*__builtin_bit_cast(float, (int)((((cast0-alu158)+127)<<23)))));
    float alu219 = ((alu1<-150.0f)?0.0f:alu218);
    float alu220 = (alu2?((float)(__builtin_nanf(""))):alu219);
    float alu221 = (alu83-((float)(cast13)));
    float alu222 = (((alu79<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu221)+0.001339262701f)*alu221)+0.009618384764f)*alu221)+0.05550347269f)*alu221)+0.2402264476f)*alu221)+0.6931471825f)*alu221)+1.0f)*__builtin_bit_cast(float, (int)(((alu184+127)<<23)))*__builtin_bit_cast(float, (int)((((cast13-alu184)+127)<<23)))));
    float alu223 = ((alu79<-150.0f)?0.0f:alu222);
    float alu224 = (alu80?((float)(__builtin_nanf(""))):alu223);
    float alu225 = (alu11-((float)(cast1)));
    float alu226 = (((alu7<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu225)+0.001339262701f)*alu225)+0.009618384764f)*alu225)+0.05550347269f)*alu225)+0.2402264476f)*alu225)+0.6931471825f)*alu225)+1.0f)*__builtin_bit_cast(float, (int)(((alu160+127)<<23)))*__builtin_bit_cast(float, (int)((((cast1-alu160)+127)<<23)))));
    float alu227 = ((alu7<-150.0f)?0.0f:alu226);
    float alu228 = (alu8?((float)(__builtin_nanf(""))):alu227);
    float alu229 = (alu89-((float)(cast14)));
    float alu230 = (((alu85<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu229)+0.001339262701f)*alu229)+0.009618384764f)*alu229)+0.05550347269f)*alu229)+0.2402264476f)*alu229)+0.6931471825f)*alu229)+1.0f)*__builtin_bit_cast(float, (int)(((alu186+127)<<23)))*__builtin_bit_cast(float, (int)((((cast14-alu186)+127)<<23)))));
    float alu231 = ((alu85<-150.0f)?0.0f:alu230);
    float alu232 = (alu86?((float)(__builtin_nanf(""))):alu231);
    float alu233 = (alu17-((float)(cast2)));
    float alu234 = (((alu13<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu233)+0.001339262701f)*alu233)+0.009618384764f)*alu233)+0.05550347269f)*alu233)+0.2402264476f)*alu233)+0.6931471825f)*alu233)+1.0f)*__builtin_bit_cast(float, (int)(((alu162+127)<<23)))*__builtin_bit_cast(float, (int)((((cast2-alu162)+127)<<23)))));
    float alu235 = ((alu13<-150.0f)?0.0f:alu234);
    float alu236 = (alu14?((float)(__builtin_nanf(""))):alu235);
    float alu237 = (alu95-((float)(cast15)));
    float alu238 = (((alu91<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu237)+0.001339262701f)*alu237)+0.009618384764f)*alu237)+0.05550347269f)*alu237)+0.2402264476f)*alu237)+0.6931471825f)*alu237)+1.0f)*__builtin_bit_cast(float, (int)(((alu188+127)<<23)))*__builtin_bit_cast(float, (int)((((cast15-alu188)+127)<<23)))));
    float alu239 = ((alu91<-150.0f)?0.0f:alu238);
    float alu240 = (alu92?((float)(__builtin_nanf(""))):alu239);
    float alu241 = (alu23-((float)(cast3)));
    float alu242 = (((alu19<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu241)+0.001339262701f)*alu241)+0.009618384764f)*alu241)+0.05550347269f)*alu241)+0.2402264476f)*alu241)+0.6931471825f)*alu241)+1.0f)*__builtin_bit_cast(float, (int)(((alu164+127)<<23)))*__builtin_bit_cast(float, (int)((((cast3-alu164)+127)<<23)))));
    float alu243 = ((alu19<-150.0f)?0.0f:alu242);
    float alu244 = (alu20?((float)(__builtin_nanf(""))):alu243);
    float alu245 = (alu101-((float)(cast16)));
    float alu246 = (((alu97<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu245)+0.001339262701f)*alu245)+0.009618384764f)*alu245)+0.05550347269f)*alu245)+0.2402264476f)*alu245)+0.6931471825f)*alu245)+1.0f)*__builtin_bit_cast(float, (int)(((alu190+127)<<23)))*__builtin_bit_cast(float, (int)((((cast16-alu190)+127)<<23)))));
    float alu247 = ((alu97<-150.0f)?0.0f:alu246);
    float alu248 = (alu98?((float)(__builtin_nanf(""))):alu247);
    float alu249 = (alu29-((float)(cast4)));
    float alu250 = (((alu25<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu249)+0.001339262701f)*alu249)+0.009618384764f)*alu249)+0.05550347269f)*alu249)+0.2402264476f)*alu249)+0.6931471825f)*alu249)+1.0f)*__builtin_bit_cast(float, (int)(((alu166+127)<<23)))*__builtin_bit_cast(float, (int)((((cast4-alu166)+127)<<23)))));
    float alu251 = ((alu25<-150.0f)?0.0f:alu250);
    float alu252 = (alu26?((float)(__builtin_nanf(""))):alu251);
    float alu253 = (alu107-((float)(cast17)));
    float alu254 = (((alu103<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu253)+0.001339262701f)*alu253)+0.009618384764f)*alu253)+0.05550347269f)*alu253)+0.2402264476f)*alu253)+0.6931471825f)*alu253)+1.0f)*__builtin_bit_cast(float, (int)(((alu192+127)<<23)))*__builtin_bit_cast(float, (int)((((cast17-alu192)+127)<<23)))));
    float alu255 = ((alu103<-150.0f)?0.0f:alu254);
    float alu256 = (alu104?((float)(__builtin_nanf(""))):alu255);
    float alu257 = (alu35-((float)(cast5)));
    float alu258 = (((alu31<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu257)+0.001339262701f)*alu257)+0.009618384764f)*alu257)+0.05550347269f)*alu257)+0.2402264476f)*alu257)+0.6931471825f)*alu257)+1.0f)*__builtin_bit_cast(float, (int)(((alu168+127)<<23)))*__builtin_bit_cast(float, (int)((((cast5-alu168)+127)<<23)))));
    float alu259 = ((alu31<-150.0f)?0.0f:alu258);
    float alu260 = (alu32?((float)(__builtin_nanf(""))):alu259);
    float alu261 = (alu113-((float)(cast18)));
    float alu262 = (((alu109<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu261)+0.001339262701f)*alu261)+0.009618384764f)*alu261)+0.05550347269f)*alu261)+0.2402264476f)*alu261)+0.6931471825f)*alu261)+1.0f)*__builtin_bit_cast(float, (int)(((alu194+127)<<23)))*__builtin_bit_cast(float, (int)((((cast18-alu194)+127)<<23)))));
    float alu263 = ((alu109<-150.0f)?0.0f:alu262);
    float alu264 = (alu110?((float)(__builtin_nanf(""))):alu263);
    float alu265 = (alu41-((float)(cast6)));
    float alu266 = (((alu37<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu265)+0.001339262701f)*alu265)+0.009618384764f)*alu265)+0.05550347269f)*alu265)+0.2402264476f)*alu265)+0.6931471825f)*alu265)+1.0f)*__builtin_bit_cast(float, (int)(((alu170+127)<<23)))*__builtin_bit_cast(float, (int)((((cast6-alu170)+127)<<23)))));
    float alu267 = ((alu37<-150.0f)?0.0f:alu266);
    float alu268 = (alu38?((float)(__builtin_nanf(""))):alu267);
    float alu269 = (alu119-((float)(cast19)));
    float alu270 = (((alu115<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu269)+0.001339262701f)*alu269)+0.009618384764f)*alu269)+0.05550347269f)*alu269)+0.2402264476f)*alu269)+0.6931471825f)*alu269)+1.0f)*__builtin_bit_cast(float, (int)(((alu196+127)<<23)))*__builtin_bit_cast(float, (int)((((cast19-alu196)+127)<<23)))));
    float alu271 = ((alu115<-150.0f)?0.0f:alu270);
    float alu272 = (alu116?((float)(__builtin_nanf(""))):alu271);
    float alu273 = (alu47-((float)(cast7)));
    float alu274 = (((alu43<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu273)+0.001339262701f)*alu273)+0.009618384764f)*alu273)+0.05550347269f)*alu273)+0.2402264476f)*alu273)+0.6931471825f)*alu273)+1.0f)*__builtin_bit_cast(float, (int)(((alu172+127)<<23)))*__builtin_bit_cast(float, (int)((((cast7-alu172)+127)<<23)))));
    float alu275 = ((alu43<-150.0f)?0.0f:alu274);
    float alu276 = (alu44?((float)(__builtin_nanf(""))):alu275);
    float alu277 = (alu125-((float)(cast20)));
    float alu278 = (((alu121<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu277)+0.001339262701f)*alu277)+0.009618384764f)*alu277)+0.05550347269f)*alu277)+0.2402264476f)*alu277)+0.6931471825f)*alu277)+1.0f)*__builtin_bit_cast(float, (int)(((alu198+127)<<23)))*__builtin_bit_cast(float, (int)((((cast20-alu198)+127)<<23)))));
    float alu279 = ((alu121<-150.0f)?0.0f:alu278);
    float alu280 = (alu122?((float)(__builtin_nanf(""))):alu279);
    float alu281 = (alu53-((float)(cast8)));
    float alu282 = (((alu49<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu281)+0.001339262701f)*alu281)+0.009618384764f)*alu281)+0.05550347269f)*alu281)+0.2402264476f)*alu281)+0.6931471825f)*alu281)+1.0f)*__builtin_bit_cast(float, (int)(((alu174+127)<<23)))*__builtin_bit_cast(float, (int)((((cast8-alu174)+127)<<23)))));
    float alu283 = ((alu49<-150.0f)?0.0f:alu282);
    float alu284 = (alu50?((float)(__builtin_nanf(""))):alu283);
    float alu285 = (alu131-((float)(cast21)));
    float alu286 = (((alu127<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu285)+0.001339262701f)*alu285)+0.009618384764f)*alu285)+0.05550347269f)*alu285)+0.2402264476f)*alu285)+0.6931471825f)*alu285)+1.0f)*__builtin_bit_cast(float, (int)(((alu200+127)<<23)))*__builtin_bit_cast(float, (int)((((cast21-alu200)+127)<<23)))));
    float alu287 = ((alu127<-150.0f)?0.0f:alu286);
    float alu288 = (alu128?((float)(__builtin_nanf(""))):alu287);
    float alu289 = (alu59-((float)(cast9)));
    float alu290 = (((alu55<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu289)+0.001339262701f)*alu289)+0.009618384764f)*alu289)+0.05550347269f)*alu289)+0.2402264476f)*alu289)+0.6931471825f)*alu289)+1.0f)*__builtin_bit_cast(float, (int)(((alu176+127)<<23)))*__builtin_bit_cast(float, (int)((((cast9-alu176)+127)<<23)))));
    float alu291 = ((alu55<-150.0f)?0.0f:alu290);
    float alu292 = (alu56?((float)(__builtin_nanf(""))):alu291);
    float alu293 = (alu137-((float)(cast22)));
    float alu294 = (((alu133<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu293)+0.001339262701f)*alu293)+0.009618384764f)*alu293)+0.05550347269f)*alu293)+0.2402264476f)*alu293)+0.6931471825f)*alu293)+1.0f)*__builtin_bit_cast(float, (int)(((alu202+127)<<23)))*__builtin_bit_cast(float, (int)((((cast22-alu202)+127)<<23)))));
    float alu295 = ((alu133<-150.0f)?0.0f:alu294);
    float alu296 = (alu134?((float)(__builtin_nanf(""))):alu295);
    float alu297 = (alu65-((float)(cast10)));
    float alu298 = (((alu61<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu297)+0.001339262701f)*alu297)+0.009618384764f)*alu297)+0.05550347269f)*alu297)+0.2402264476f)*alu297)+0.6931471825f)*alu297)+1.0f)*__builtin_bit_cast(float, (int)(((alu178+127)<<23)))*__builtin_bit_cast(float, (int)((((cast10-alu178)+127)<<23)))));
    float alu299 = ((alu61<-150.0f)?0.0f:alu298);
    float alu300 = (alu62?((float)(__builtin_nanf(""))):alu299);
    float alu301 = (alu143-((float)(cast23)));
    float alu302 = (((alu139<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu301)+0.001339262701f)*alu301)+0.009618384764f)*alu301)+0.05550347269f)*alu301)+0.2402264476f)*alu301)+0.6931471825f)*alu301)+1.0f)*__builtin_bit_cast(float, (int)(((alu204+127)<<23)))*__builtin_bit_cast(float, (int)((((cast23-alu204)+127)<<23)))));
    float alu303 = ((alu139<-150.0f)?0.0f:alu302);
    float alu304 = (alu140?((float)(__builtin_nanf(""))):alu303);
    float alu305 = (alu71-((float)(cast11)));
    float alu306 = (((alu67<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu305)+0.001339262701f)*alu305)+0.009618384764f)*alu305)+0.05550347269f)*alu305)+0.2402264476f)*alu305)+0.6931471825f)*alu305)+1.0f)*__builtin_bit_cast(float, (int)(((alu180+127)<<23)))*__builtin_bit_cast(float, (int)((((cast11-alu180)+127)<<23)))));
    float alu307 = ((alu67<-150.0f)?0.0f:alu306);
    float alu308 = (alu68?((float)(__builtin_nanf(""))):alu307);
    float alu309 = (alu149-((float)(cast24)));
    float alu310 = (((alu145<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu309)+0.001339262701f)*alu309)+0.009618384764f)*alu309)+0.05550347269f)*alu309)+0.2402264476f)*alu309)+0.6931471825f)*alu309)+1.0f)*__builtin_bit_cast(float, (int)(((alu206+127)<<23)))*__builtin_bit_cast(float, (int)((((cast24-alu206)+127)<<23)))));
    float alu311 = ((alu145<-150.0f)?0.0f:alu310);
    float alu312 = (alu146?((float)(__builtin_nanf(""))):alu311);
    *(data0_16+Lidx1) = (1.0f/(alu216+alu217+alu220+alu224+alu228+alu232+alu236+alu240+alu244+alu248+alu252+alu256+alu260+alu264+alu268+alu272+alu276+alu280+alu284+alu288+alu292+alu296+alu300+alu304+alu308+alu312));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_4_16_25_16_4n2(float* restrict data0_256, float* restrict data1_416, float* restrict data2_16, float* restrict data3_16, float* restrict data4_1600, float* restrict data5_256, float* restrict data6_4096, float* restrict data7_64) {
  float acc0[1];
  float acc1[1];
  for (int Lidx2 = 0; Lidx2 < 4; Lidx2++) {
    int alu0 = (Lidx2*104);
    for (int Lidx3 = 0; Lidx3 < 4; Lidx3++) {
      int alu1 = ((Lidx2<<2)+Lidx3);
      float val0 = (*(data2_16+alu1));
      float val1 = (*(data3_16+alu1));
      int alu2 = (Lidx3*26);
      float val2 = (*(data1_416+(alu0+alu2+25)));
      float alu3 = ((val2-val0)*1.4426950408889634f);
      _Bool alu4 = (alu3!=alu3);
      float alu5 = ((alu3!=((float)(-__builtin_inff())))?alu3:0.0f);
      float alu6 = (alu4?0.0f:alu5);
      float alu7 = ((alu3!=((float)(__builtin_inff())))?alu6:0.0f);
      float alu8 = ((alu7<0.0f)?-0.5f:0.5f);
      int cast0 = ((int)((alu7+alu8)));
      int alu9 = ((cast0<0)?1:0);
      int alu10 = ((cast0+alu9)>>1);
      float alu11 = (alu7-((float)(cast0)));
      float alu12 = (((alu3<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu11)+0.001339262701f)*alu11)+0.009618384764f)*alu11)+0.05550347269f)*alu11)+0.2402264476f)*alu11)+0.6931471825f)*alu11)+1.0f)*__builtin_bit_cast(float, (int)(((alu10+127)<<23)))*__builtin_bit_cast(float, (int)((((cast0-alu10)+127)<<23)))));
      float alu13 = ((alu3<-150.0f)?0.0f:alu12);
      float alu14 = (alu4?((float)(__builtin_nanf(""))):alu13);
      for (int Lidx4 = 0; Lidx4 < 16; Lidx4++) {
        *(acc1+0) = 0.0f;
        for (int Ridx0 = 0; Ridx0 < 25; Ridx0++) {
          float val3 = (*(data1_416+(alu2+Ridx0+alu0)));
          float val4 = (*(data4_1600+((Ridx0<<4)+Lidx4+(Lidx2*400))));
          float alu16 = ((val3-val0)*1.4426950408889634f);
          _Bool alu17 = (alu16!=alu16);
          float alu18 = ((alu16!=((float)(-__builtin_inff())))?alu16:0.0f);
          float alu19 = (alu17?0.0f:alu18);
          float alu20 = ((alu16!=((float)(__builtin_inff())))?alu19:0.0f);
          float alu21 = ((alu20<0.0f)?-0.5f:0.5f);
          int cast1 = ((int)((alu20+alu21)));
          int alu22 = ((cast1<0)?1:0);
          int alu23 = ((cast1+alu22)>>1);
          float alu24 = (alu20-((float)(cast1)));
          float alu25 = (((alu16<128.0f)!=1)?((float)(__builtin_inff())):(((((((((((((0.0001535920892f*alu24)+0.001339262701f)*alu24)+0.009618384764f)*alu24)+0.05550347269f)*alu24)+0.2402264476f)*alu24)+0.6931471825f)*alu24)+1.0f)*__builtin_bit_cast(float, (int)(((alu23+127)<<23)))*__builtin_bit_cast(float, (int)((((cast1-alu23)+127)<<23)))));
          float alu26 = ((alu16<-150.0f)?0.0f:alu25);
          float alu27 = (alu17?((float)(__builtin_nanf(""))):alu26);
          *(acc1+0) = ((*(acc1+0))+(alu27*val4));
        }
        int alu30 = ((Lidx2<<4)+Lidx4);
        *(acc0+0) = 0.0f;
        for (int Ridx1 = 0; Ridx1 < 16; Ridx1++) {
          int alu32 = (alu30+(Ridx1<<8));
          float val5 = (*(data6_4096+(alu32+64)));
          float val6 = (*(data6_4096+(alu32+128)));
          float val7 = (*(data6_4096+(alu32+192)));
          float val8 = (*(data6_4096+alu32));
          float4 val9 = (*((float4*)((data5_256+((Ridx1<<2)+(Lidx3<<6))))));
          *(acc0+0) = ((*(acc0+0))+(val9[0]*val8)+(val9[1]*val5)+(val9[2]*val6)+(val9[3]*val7));
        }
        float val10 = (*(data7_64+alu30));
        *(data0_256+((Lidx3<<4)+Lidx4+(Lidx2<<6))) = (((*(acc1+0))*val1)+(alu14*val1*((*(acc0+0))+val10)));
      }
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_64_4_16n2(float* restrict data0_256, float* restrict data1_256, float* restrict data2_256, float* restrict data3_4096, float* restrict data4_64) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 64; Lidx2++) {
      *(acc0+0) = 0.0f;
      for (int Ridx0_0 = 0; Ridx0_0 < 4; Ridx0_0++) {
        int alu1 = ((Ridx0_0<<10)+Lidx2);
        float val0 = (*(data3_4096+(alu1+64)));
        float val1 = (*(data3_4096+(alu1+128)));
        float val2 = (*(data3_4096+(alu1+192)));
        float val3 = (*(data3_4096+(alu1+256)));
        float val4 = (*(data3_4096+(alu1+320)));
        float val5 = (*(data3_4096+(alu1+384)));
        float val6 = (*(data3_4096+(alu1+448)));
        float val7 = (*(data3_4096+(alu1+512)));
        float val8 = (*(data3_4096+(alu1+576)));
        float val9 = (*(data3_4096+(alu1+640)));
        float val10 = (*(data3_4096+(alu1+704)));
        float val11 = (*(data3_4096+(alu1+768)));
        float val12 = (*(data3_4096+(alu1+832)));
        float val13 = (*(data3_4096+(alu1+896)));
        float val14 = (*(data3_4096+(alu1+960)));
        float val15 = (*(data3_4096+alu1));
        int alu2 = ((Ridx0_0<<6)+(Lidx1<<4));
        float4 val16 = (*((float4*)((data2_256+(alu2+4)))));
        float4 val17 = (*((float4*)((data2_256+(alu2+8)))));
        float4 val18 = (*((float4*)((data2_256+(alu2+12)))));
        float4 val19 = (*((float4*)((data2_256+alu2))));
        *(acc0+0) = ((*(acc0+0))+(val19[0]*val15)+(val19[1]*val0)+(val19[2]*val1)+(val19[3]*val2)+(val16[0]*val3)+(val16[1]*val4)+(val16[2]*val5)+(val16[3]*val6)+(val17[0]*val7)+(val17[1]*val8)+(val17[2]*val9)+(val17[3]*val10)+(val18[0]*val11)+(val18[1]*val12)+(val18[2]*val13)+(val18[3]*val14));
      }
      int alu5 = ((Lidx1<<6)+Lidx2);
      float val20 = (*(data1_256+alu5));
      float val21 = (*(data4_64+Lidx2));
      *(data0_256+alu5) = (val20+(*(acc0+0))+val21);
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4n8(float* restrict data0_4, float* restrict data1_256) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val0 = (*((float4*)((data1_256+((Ridx0<<2)+(Lidx1<<6))))));
      *(acc0+0) = ((*(acc0+0))+val0[0]+val0[1]+val0[2]+val0[3]);
    }
    *(data0_4+Lidx1) = ((*(acc0+0))*0.015625f);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4n9(float* restrict data0_4, float* restrict data1_256, float* restrict data2_4) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    float val0 = (*(data2_4+Lidx1));
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val1 = (*((float4*)((data1_256+((Ridx0<<2)+(Lidx1<<6))))));
      float alu1 = (val1[0]-val0);
      float alu2 = (val1[1]-val0);
      float alu3 = (val1[2]-val0);
      float alu4 = (val1[3]-val0);
      *(acc0+0) = ((*(acc0+0))+(alu1*alu1)+(alu2*alu2)+(alu3*alu3)+(alu4*alu4));
    }
    *(data0_4+Lidx1) = (1.0f/__builtin_sqrtf((((*(acc0+0))*0.015625f)+1e-05f)));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_E_4_16_4n4(float* restrict data0_256, float* restrict data1_256, float* restrict data2_4, float* restrict data3_4, float* restrict data4_64, float* restrict data5_64) {
  for (int Lidx0 = 0; Lidx0 < 4; Lidx0++) {
    float val0 = (*(data2_4+Lidx0));
    float val1 = (*(data3_4+Lidx0));
    for (int Lidx1 = 0; Lidx1 < 16; Lidx1++) {
      int alu0 = (Lidx1<<2);
      int alu1 = ((Lidx0<<6)+alu0);
      float4 val2 = (*((float4*)((data1_256+alu1))));
      float4 val3 = (*((float4*)((data4_64+alu0))));
      float4 val4 = (*((float4*)((data5_64+alu0))));
      *((float4*)((data0_256+alu1))) = (float4){(((val2[0]-val0)*val1*val3[0])+val4[0]),(((val2[1]-val0)*val1*val3[1])+val4[1]),(((val2[2]-val0)*val1*val3[2])+val4[2]),(((val2[3]-val0)*val1*val3[3])+val4[3])};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_128_4_16_4n2(float* restrict data0_512, float* restrict data1_256, float* restrict data2_8192, float* restrict data3_128) {
  float acc0[4];
  for (int Lidx2 = 0; Lidx2 < 128; Lidx2++) {
    *(acc0+0) = 0.0f;
    *(acc0+1) = 0.0f;
    *(acc0+2) = 0.0f;
    *(acc0+3) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      int alu4 = ((Ridx0<<9)+Lidx2);
      float val0 = (*(data2_8192+(alu4+128)));
      float val1 = (*(data2_8192+(alu4+256)));
      float val2 = (*(data2_8192+(alu4+384)));
      float val3 = (*(data2_8192+alu4));
      int alu5 = (Ridx0<<2);
      float4 val4 = (*((float4*)((data1_256+(alu5+64)))));
      float4 val5 = (*((float4*)((data1_256+(alu5+128)))));
      float4 val6 = (*((float4*)((data1_256+(alu5+192)))));
      float4 val7 = (*((float4*)((data1_256+alu5))));
      *(acc0+0) = ((*(acc0+0))+(val7[0]*val3)+(val7[1]*val0)+(val7[2]*val1)+(val7[3]*val2));
      *(acc0+1) = ((*(acc0+1))+(val4[0]*val3)+(val4[1]*val0)+(val4[2]*val1)+(val4[3]*val2));
      *(acc0+2) = ((*(acc0+2))+(val5[0]*val3)+(val5[1]*val0)+(val5[2]*val1)+(val5[3]*val2));
      *(acc0+3) = ((*(acc0+3))+(val6[0]*val3)+(val6[1]*val0)+(val6[2]*val1)+(val6[3]*val2));
    }
    float val8 = (*(data3_128+Lidx2));
    float alu11 = ((*(acc0+0))+val8);
    float alu12 = ((*(acc0+1))+val8);
    float alu13 = ((*(acc0+2))+val8);
    float alu14 = ((*(acc0+3))+val8);
    float alu15 = ((0.0f<alu11)?alu11:0.0f);
    float alu16 = ((0.0f<alu12)?alu12:0.0f);
    float alu17 = ((0.0f<alu13)?alu13:0.0f);
    float alu18 = ((0.0f<alu14)?alu14:0.0f);
    *(data0_512+(Lidx2+128)) = alu16;
    *(data0_512+(Lidx2+256)) = alu17;
    *(data0_512+(Lidx2+384)) = alu18;
    *(data0_512+Lidx2) = alu15;
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_64_32_4n2(float* restrict data0_256, float* restrict data1_256, float* restrict data2_512, float* restrict data3_8192, float* restrict data4_64) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 64; Lidx2++) {
      *(acc0+0) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 32; Ridx0++) {
        int alu1 = ((Ridx0<<8)+Lidx2);
        float val0 = (*(data3_8192+(alu1+64)));
        float val1 = (*(data3_8192+(alu1+128)));
        float val2 = (*(data3_8192+(alu1+192)));
        float val3 = (*(data3_8192+alu1));
        float4 val4 = (*((float4*)((data2_512+((Ridx0<<2)+(Lidx1<<7))))));
        *(acc0+0) = ((*(acc0+0))+(val4[0]*val3)+(val4[1]*val0)+(val4[2]*val1)+(val4[3]*val2));
      }
      int alu4 = ((Lidx1<<6)+Lidx2);
      float val5 = (*(data1_256+alu4));
      float val6 = (*(data4_64+Lidx2));
      *(data0_256+alu4) = (val5+(*(acc0+0))+val6);
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4n10(float* restrict data0_4, float* restrict data1_256) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val0 = (*((float4*)((data1_256+((Ridx0<<2)+(Lidx1<<6))))));
      *(acc0+0) = ((*(acc0+0))+val0[0]+val0[1]+val0[2]+val0[3]);
    }
    *(data0_4+Lidx1) = ((*(acc0+0))*0.015625f);
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_16_4n11(float* restrict data0_4, float* restrict data1_256, float* restrict data2_4) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    float val0 = (*(data2_4+Lidx1));
    *(acc0+0) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 16; Ridx0++) {
      float4 val1 = (*((float4*)((data1_256+((Ridx0<<2)+(Lidx1<<6))))));
      float alu1 = (val1[0]-val0);
      float alu2 = (val1[1]-val0);
      float alu3 = (val1[2]-val0);
      float alu4 = (val1[3]-val0);
      *(acc0+0) = ((*(acc0+0))+(alu1*alu1)+(alu2*alu2)+(alu3*alu3)+(alu4*alu4));
    }
    *(data0_4+Lidx1) = (1.0f/__builtin_sqrtf((((*(acc0+0))*0.015625f)+1e-05f)));
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_E_4_40_4n1(float* restrict data0_640, float* restrict data1_96, float* restrict data2_256, float* restrict data3_4, float* restrict data4_4, float* restrict data5_64, float* restrict data6_64) {
  float4 cast0 = (float4){0.0f,0.0f,0.0f,0.0f};
  for (int Lidx0 = 0; Lidx0 < 4; Lidx0++) {
    float val0 = (*(data3_4+Lidx0));
    float val1 = (*(data4_4+Lidx0));
    for (int Lidx1 = 0; Lidx1 < 40; Lidx1++) {
      int alu0 = (Lidx1<<2);
      _Bool alu1 = (Lidx1<24);
      float4 val2 = (alu1?*((float4*)((data1_96+alu0))):cast0);
      _Bool alu2 = (23<Lidx1);
      float4 val3 = (alu2?*((float4*)((data2_256+((Lidx0<<6)+alu0+-96)))):cast0);
      int alu3 = (alu0+-96);
      float4 val4 = (alu2?*((float4*)((data5_64+alu3))):cast0);
      float4 val5 = (alu2?*((float4*)((data6_64+alu3))):cast0);
      float alu4 = (alu1?0.0f:(((val3[0]-val0)*val1*val4[0])+val5[0]));
      float alu5 = (alu1?0.0f:(((val3[1]-val0)*val1*val4[1])+val5[1]));
      float alu6 = (alu1?0.0f:(((val3[2]-val0)*val1*val4[2])+val5[2]));
      float alu7 = (alu1?0.0f:(((val3[3]-val0)*val1*val4[3])+val5[3]));
      *((float4*)((data0_640+((Lidx0*160)+alu0)))) = (float4){(val2[0]+alu4),(val2[1]+alu5),(val2[2]+alu6),(val2[3]+alu7)};
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_256_4_40_4n1(float* restrict data0_1024, float* restrict data1_640, float* restrict data2_40960, float* restrict data3_256) {
  float acc0[4];
  for (int Lidx2 = 0; Lidx2 < 256; Lidx2++) {
    *(acc0+0) = 0.0f;
    *(acc0+1) = 0.0f;
    *(acc0+2) = 0.0f;
    *(acc0+3) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 40; Ridx0++) {
      int alu4 = ((Ridx0<<10)+Lidx2);
      float val0 = (*(data2_40960+(alu4+256)));
      float val1 = (*(data2_40960+(alu4+512)));
      float val2 = (*(data2_40960+(alu4+768)));
      float val3 = (*(data2_40960+alu4));
      int alu5 = (Ridx0<<2);
      float4 val4 = (*((float4*)((data1_640+(alu5+160)))));
      float4 val5 = (*((float4*)((data1_640+(alu5+320)))));
      float4 val6 = (*((float4*)((data1_640+(alu5+480)))));
      float4 val7 = (*((float4*)((data1_640+alu5))));
      *(acc0+0) = ((*(acc0+0))+(val7[0]*val3)+(val7[1]*val0)+(val7[2]*val1)+(val7[3]*val2));
      *(acc0+1) = ((*(acc0+1))+(val4[0]*val3)+(val4[1]*val0)+(val4[2]*val1)+(val4[3]*val2));
      *(acc0+2) = ((*(acc0+2))+(val5[0]*val3)+(val5[1]*val0)+(val5[2]*val1)+(val5[3]*val2));
      *(acc0+3) = ((*(acc0+3))+(val6[0]*val3)+(val6[1]*val0)+(val6[2]*val1)+(val6[3]*val2));
    }
    float val8 = (*(data3_256+Lidx2));
    float alu11 = ((*(acc0+0))+val8);
    float alu12 = ((*(acc0+1))+val8);
    float alu13 = ((*(acc0+2))+val8);
    float alu14 = ((*(acc0+3))+val8);
    float alu15 = ((0.0f<alu11)?alu11:0.0f);
    float alu16 = ((0.0f<alu12)?alu12:0.0f);
    float alu17 = ((0.0f<alu13)?alu13:0.0f);
    float alu18 = ((0.0f<alu14)?alu14:0.0f);
    *(data0_1024+(Lidx2+256)) = alu16;
    *(data0_1024+(Lidx2+512)) = alu17;
    *(data0_1024+(Lidx2+768)) = alu18;
    *(data0_1024+Lidx2) = alu15;
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_96_64_4n1(float* restrict data0_384, float* restrict data1_96, float* restrict data2_1024, float* restrict data3_24576, float* restrict data4_96) {
  float acc0[1];
  for (int Lidx1 = 0; Lidx1 < 4; Lidx1++) {
    for (int Lidx2 = 0; Lidx2 < 96; Lidx2++) {
      *(acc0+0) = 0.0f;
      for (int Ridx0 = 0; Ridx0 < 64; Ridx0++) {
        int alu1 = ((Ridx0*384)+Lidx2);
        float val0 = (*(data3_24576+(alu1+96)));
        float val1 = (*(data3_24576+(alu1+192)));
        float val2 = (*(data3_24576+(alu1+288)));
        float val3 = (*(data3_24576+alu1));
        float4 val4 = (*((float4*)((data2_1024+((Ridx0<<2)+(Lidx1<<8))))));
        *(acc0+0) = ((*(acc0+0))+(val4[0]*val3)+(val4[1]*val0)+(val4[2]*val1)+(val4[3]*val2));
      }
      float val5 = (*(data1_96+Lidx2));
      float val6 = (*(data4_96+Lidx2));
      *(data0_384+((Lidx1*96)+Lidx2)) = (val5+(*(acc0+0))+val6);
    }
  }
}

typedef float float4 __attribute__((aligned(16),ext_vector_type(4)));
void jepa_predict4_r_4_96_16_4n1(float* restrict data0_4, float* restrict data1_384, float* restrict data2_6144, float* restrict data3_64, float* restrict data4_64, float* restrict data5_1) {
  float acc0[16];
  float acc1[4];
  *(acc1+0) = 0.0f;
  *(acc1+1) = 0.0f;
  *(acc1+2) = 0.0f;
  *(acc1+3) = 0.0f;
  for (int Ridx1 = 0; Ridx1 < 16; Ridx1++) {
    int alu4 = (Ridx1<<2);
    *(acc0+0) = 0.0f;
    *(acc0+1) = 0.0f;
    *(acc0+2) = 0.0f;
    *(acc0+3) = 0.0f;
    *(acc0+4) = 0.0f;
    *(acc0+5) = 0.0f;
    *(acc0+6) = 0.0f;
    *(acc0+7) = 0.0f;
    *(acc0+8) = 0.0f;
    *(acc0+9) = 0.0f;
    *(acc0+10) = 0.0f;
    *(acc0+11) = 0.0f;
    *(acc0+12) = 0.0f;
    *(acc0+13) = 0.0f;
    *(acc0+14) = 0.0f;
    *(acc0+15) = 0.0f;
    for (int Ridx0 = 0; Ridx0 < 96; Ridx0++) {
      float val0 = (*(data1_384+Ridx0));
      float val1 = (*(data1_384+(Ridx0+96)));
      float val2 = (*(data1_384+(Ridx0+192)));
      float val3 = (*(data1_384+(Ridx0+288)));
      float4 val4 = (*((float4*)((data2_6144+((Ridx0<<6)+alu4)))));
      *(acc0+0) = ((*(acc0+0))+(val0*val4[0]));
      *(acc0+1) = ((*(acc0+1))+(val0*val4[1]));
      *(acc0+2) = ((*(acc0+2))+(val0*val4[2]));
      *(acc0+3) = ((*(acc0+3))+(val0*val4[3]));
      *(acc0+4) = ((*(acc0+4))+(val1*val4[0]));
      *(acc0+5) = ((*(acc0+5))+(val1*val4[1]));
      *(acc0+6) = ((*(acc0+6))+(val1*val4[2]));
      *(acc0+7) = ((*(acc0+7))+(val1*val4[3]));
      *(acc0+8) = ((*(acc0+8))+(val2*val4[0]));
      *(acc0+9) = ((*(acc0+9))+(val2*val4[1]));
      *(acc0+10) = ((*(acc0+10))+(val2*val4[2]));
      *(acc0+11) = ((*(acc0+11))+(val2*val4[3]));
      *(acc0+12) = ((*(acc0+12))+(val3*val4[0]));
      *(acc0+13) = ((*(acc0+13))+(val3*val4[1]));
      *(acc0+14) = ((*(acc0+14))+(val3*val4[2]));
      *(acc0+15) = ((*(acc0+15))+(val3*val4[3]));
    }
    float4 val5 = (*((float4*)((data3_64+alu4))));
    float4 val6 = (*((float4*)((data4_64+alu4))));
    float alu38 = ((*(acc0+0))+val5[0]);
    float alu39 = ((0.0f<alu38)?alu38:0.0f);
    float alu40 = ((*(acc0+1))+val5[1]);
    float alu41 = ((*(acc0+2))+val5[2]);
    float alu42 = ((*(acc0+3))+val5[3]);
    float alu43 = ((*(acc0+4))+val5[0]);
    float alu44 = ((0.0f<alu43)?alu43:0.0f);
    float alu45 = ((*(acc0+5))+val5[1]);
    float alu46 = ((*(acc0+6))+val5[2]);
    float alu47 = ((*(acc0+7))+val5[3]);
    float alu48 = ((*(acc0+8))+val5[0]);
    float alu49 = ((0.0f<alu48)?alu48:0.0f);
    float alu50 = ((*(acc0+9))+val5[1]);
    float alu51 = ((*(acc0+10))+val5[2]);
    float alu52 = ((*(acc0+11))+val5[3]);
    float alu53 = ((*(acc0+12))+val5[0]);
    float alu54 = ((0.0f<alu53)?alu53:0.0f);
    float alu55 = ((*(acc0+13))+val5[1]);
    float alu56 = ((*(acc0+14))+val5[2]);
    float alu57 = ((*(acc0+15))+val5[3]);
    float alu58 = ((0.0f<alu40)?alu40:0.0f);
    float alu59 = ((0.0f<alu45)?alu45:0.0f);
    float alu60 = ((0.0f<alu50)?alu50:0.0f);
    float alu61 = ((0.0f<alu55)?alu55:0.0f);
    float alu62 = ((0.0f<alu41)?alu41:0.0f);
    float alu63 = ((0.0f<alu46)?alu46:0.0f);
    float alu64 = ((0.0f<alu51)?alu51:0.0f);
    float alu65 = ((0.0f<alu56)?alu56:0.0f);
    float alu66 = ((0.0f<alu42)?alu42:0.0f);
    float alu67 = ((0.0f<alu47)?alu47:0.0f);
    float alu68 = ((0.0f<alu52)?alu52:0.0f);
    float alu69 = ((0.0f<alu57)?alu57:0.0f);
    *(acc1+0) = ((*(acc1+0))+(alu39*val6[0])+(alu58*val6[1])+(alu62*val6[2])+(alu66*val6[3]));
    *(acc1+1) = ((*(acc1+1))+(alu44*val6[0])+(alu59*val6[1])+(alu63*val6[2])+(alu67*val6[3]));
    *(acc1+2) = ((*(acc1+2))+(alu49*val6[0])+(alu60*val6[1])+(alu64*val6[2])+(alu68*val6[3]));
    *(acc1+3) = ((*(acc1+3))+(alu54*val6[0])+(alu61*val6[1])+(alu65*val6[2])+(alu69*val6[3]));
  }
  float val7 = (*(data5_1+0));
  *((float4*)((data0_4+0))) = (float4){((*(acc1+0))+val7),((*(acc1+1))+val7),((*(acc1+2))+val7),((*(acc1+3))+val7)};
}

void* jepa_predict4_bufs[48];
void jepa_predict4_set_buf(size_t index, void* ptr) {
  jepa_predict4_bufs[index] = ptr;
}
float jepa_predict4_buf_11[256];
float jepa_predict4_buf_10[4];
float jepa_predict4_buf_31[512];
float jepa_predict4_buf_14[256];
float jepa_predict4_buf_20[16];
float jepa_predict4_buf_37[256];
float jepa_predict4_buf_45[256];
float jepa_predict4_buf_34[256];
float jepa_predict4_buf_28[4];
float jepa_predict4_buf_6[256];
float jepa_predict4_buf_56[640];
float jepa_predict4_buf_42[416];
float jepa_predict4_buf_4[64];
float jepa_predict4_buf_0[312];
float jepa_predict4_buf_17[416];
float jepa_predict4_buf_24[256];
float jepa_predict4_buf_9[4];
float jepa_predict4_buf_27[4];
float jepa_predict4_buf_59[1024];
float jepa_predict4_buf_21[16];
void jepa_predict4_net(float* output0,float* output1,float* input0,float* input1,float* input2,float* input3,float* input4,float* input5,float* input6,int* input7,int* input8)
{
  jepa_predict4_E_78_4n1(jepa_predict4_buf_0, input6, input7, (float *)jepa_predict4_bufs[0], (float *)jepa_predict4_bufs[1], (float *)jepa_predict4_bufs[2]);
  jepa_predict4_E_16_4n1(jepa_predict4_buf_4, input8, (float *)jepa_predict4_bufs[3]);
  jepa_predict4_r_4_16_4_78n1(jepa_predict4_buf_6, jepa_predict4_buf_0, (float *)jepa_predict4_bufs[4], (float *)jepa_predict4_bufs[5], jepa_predict4_buf_4);
  jepa_predict4_r_4_16_4n2(jepa_predict4_buf_9, jepa_predict4_buf_6);
  jepa_predict4_r_4_16_4n3(jepa_predict4_buf_10, jepa_predict4_buf_6, jepa_predict4_buf_9);
  jepa_predict4_E_4_16_4n1(jepa_predict4_buf_11, jepa_predict4_buf_6, jepa_predict4_buf_9, jepa_predict4_buf_10, (float *)jepa_predict4_bufs[6], (float *)jepa_predict4_bufs[7]);
  jepa_predict4_r_4_64_16_4n1(jepa_predict4_buf_14, jepa_predict4_buf_11, (float *)jepa_predict4_bufs[8], (float *)jepa_predict4_bufs[9]);
  jepa_predict4_r_4_4_26_16_64_16n1(jepa_predict4_buf_17, jepa_predict4_buf_14, input1, jepa_predict4_buf_11, (float *)jepa_predict4_bufs[10], (float *)jepa_predict4_bufs[11], input5);
  jepa_predict4_r_16_26n2(jepa_predict4_buf_20, jepa_predict4_buf_17);
  jepa_predict4_r_16_26n3(jepa_predict4_buf_21, jepa_predict4_buf_17, jepa_predict4_buf_20);
  jepa_predict4_r_4_4_16_25_16_4n1(jepa_predict4_buf_14, jepa_predict4_buf_17, jepa_predict4_buf_20, jepa_predict4_buf_21, input2, jepa_predict4_buf_11, (float *)jepa_predict4_bufs[12], (float *)jepa_predict4_bufs[13]);
  jepa_predict4_r_4_64_4_16n1(jepa_predict4_buf_24, jepa_predict4_buf_6, jepa_predict4_buf_14, (float *)jepa_predict4_bufs[14], (float *)jepa_predict4_bufs[15]);
  jepa_predict4_r_4_16_4n4(jepa_predict4_buf_27, jepa_predict4_buf_24);
  jepa_predict4_r_4_16_4n5(jepa_predict4_buf_28, jepa_predict4_buf_24, jepa_predict4_buf_27);
  jepa_predict4_E_4_16_4n2(jepa_predict4_buf_6, jepa_predict4_buf_24, jepa_predict4_buf_27, jepa_predict4_buf_28, (float *)jepa_predict4_bufs[16], (float *)jepa_predict4_bufs[17]);
  jepa_predict4_r_128_4_16_4n1(jepa_predict4_buf_31, jepa_predict4_buf_6, (float *)jepa_predict4_bufs[18], (float *)jepa_predict4_bufs[19]);
  jepa_predict4_r_4_64_32_4n1(jepa_predict4_buf_34, jepa_predict4_buf_24, jepa_predict4_buf_31, (float *)jepa_predict4_bufs[20], (float *)jepa_predict4_bufs[21]);
  jepa_predict4_r_4_16_4n6(jepa_predict4_buf_9, jepa_predict4_buf_34);
  jepa_predict4_r_4_16_4n7(jepa_predict4_buf_10, jepa_predict4_buf_34, jepa_predict4_buf_9);
  jepa_predict4_E_4_16_4n3(jepa_predict4_buf_37, jepa_predict4_buf_34, jepa_predict4_buf_9, jepa_predict4_buf_10, (float *)jepa_predict4_bufs[22], (float *)jepa_predict4_bufs[23]);
  jepa_predict4_r_4_64_16_4n2(jepa_predict4_buf_24, jepa_predict4_buf_37, (float *)jepa_predict4_bufs[24], (float *)jepa_predict4_bufs[25]);
  jepa_predict4_r_4_4_26_16_64_16n2(jepa_predict4_buf_42, jepa_predict4_buf_24, input3, jepa_predict4_buf_37, (float *)jepa_predict4_bufs[26], (float *)jepa_predict4_bufs[27], input5);
  jepa_predict4_r_16_26n4(jepa_predict4_buf_20, jepa_predict4_buf_42);
  jepa_predict4_r_16_26n5(jepa_predict4_buf_21, jepa_predict4_buf_42, jepa_predict4_buf_20);
  jepa_predict4_r_4_4_16_25_16_4n2(jepa_predict4_buf_45, jepa_predict4_buf_42, jepa_predict4_buf_20, jepa_predict4_buf_21, input4, jepa_predict4_buf_37, (float *)jepa_predict4_bufs[28], (float *)jepa_predict4_bufs[29]);
  jepa_predict4_r_4_64_4_16n2(jepa_predict4_buf_24, jepa_predict4_buf_34, jepa_predict4_buf_45, (float *)jepa_predict4_bufs[30], (float *)jepa_predict4_bufs[31]);
  jepa_predict4_r_4_16_4n8(jepa_predict4_buf_27, jepa_predict4_buf_24);
  jepa_predict4_r_4_16_4n9(jepa_predict4_buf_28, jepa_predict4_buf_24, jepa_predict4_buf_27);
  jepa_predict4_E_4_16_4n4(jepa_predict4_buf_6, jepa_predict4_buf_24, jepa_predict4_buf_27, jepa_predict4_buf_28, (float *)jepa_predict4_bufs[32], (float *)jepa_predict4_bufs[33]);
  jepa_predict4_r_128_4_16_4n2(jepa_predict4_buf_31, jepa_predict4_buf_6, (float *)jepa_predict4_bufs[34], (float *)jepa_predict4_bufs[35]);
  jepa_predict4_r_4_64_32_4n2(jepa_predict4_buf_34, jepa_predict4_buf_24, jepa_predict4_buf_31, (float *)jepa_predict4_bufs[36], (float *)jepa_predict4_bufs[37]);
  jepa_predict4_r_4_16_4n10(jepa_predict4_buf_9, jepa_predict4_buf_34);
  jepa_predict4_r_4_16_4n11(jepa_predict4_buf_10, jepa_predict4_buf_34, jepa_predict4_buf_9);
  jepa_predict4_E_4_40_4n1(jepa_predict4_buf_56, input0, jepa_predict4_buf_34, jepa_predict4_buf_9, jepa_predict4_buf_10, (float *)jepa_predict4_bufs[38], (float *)jepa_predict4_bufs[39]);
  jepa_predict4_r_256_4_40_4n1(jepa_predict4_buf_59, jepa_predict4_buf_56, (float *)jepa_predict4_bufs[40], (float *)jepa_predict4_bufs[41]);
  jepa_predict4_r_4_96_64_4n1(output0, input0, jepa_predict4_buf_59, (float *)jepa_predict4_bufs[42], (float *)jepa_predict4_bufs[43]);
  jepa_predict4_r_4_96_16_4n1(output1, output0, (float *)jepa_predict4_bufs[44], (float *)jepa_predict4_bufs[45], (float *)jepa_predict4_bufs[46], (float *)jepa_predict4_bufs[47]);
}