[TOC]

_**NOTE: This test runs with `inter_op_parallelism_threads=0` which means TensorFlow automatically determines size of the thread pool. This setting causes problems. See more detail reason and data in [this test](https://github.com/lcy-seso/dl_framework/blob/master/tensorflow/data_parallelism_for_nmt/docs/inter_op_parallelism_threads_with_MKL.md).**_

# `tf.contrib.cudnn_rnn.CudnnLSTM` for encoder and decoder

- Data collected based on this commit [dd8cd72](https://github.com/lcy-seso/dl_framework/tree/dd8cd72468774604d39daefc7570e6e786eab7a5/tensorflow/data_parallelism_for_nmt)

- Commandline to run the test:

  ```bash
  CUDA_VISIBLE_DEVICES="x,...,x" python train.py \
    --encoder_type="cudnn_lstm" \
    --direction="bi" \
    --batch_size=360 \
    --variable_update="parameter_server" \
    2>&1 | tee train.log
  ```

  - **NOTE: the current implementation cannot use NCCL allreduce to merge gradients**.

## Use WMT 14 En-De

- [cudnn_lstm](https://www.tensorflow.org/api_docs/python/tf/contrib/cudnn_rnn/CudnnLSTM) encoder and decoder.

  |GPU number|Batch size|Total time to process 20 batches (s)|Processing speed (words/s)|Speedup ratio|
  |:--|:--|:--|:--|:--|
  |1|360|29.217|49532.893||
  |2|360|33.618|86096.435|1.74|
  |3|360|48.257|89968.832|1.82|
  |4|360|53.618|107964.402|2.18|
  |5|360|64.983|111351.868|2.25|
  |6|360|71.581|121305.375|2.45|
  |7|360|86.774|116744.428|2.36|
  |8|360|97.896|118263.894|2.39|

- I directly copy the test result when using [dynamic_rnn](https://www.tensorflow.org/api_docs/python/tf/nn/dynamic_rnn) encoder and decoder for comparison.

  |GPU number|batch size per GPU|total time to run 20 batches(s)|processing speed (words/second)|speed-up ratio|
  |:--|:--|:--|:--|:--|
  |1|360|40.574|35668.346||
  |2|360|47.222|61293.843|1.72|
  |3|360|58.628|74052.914|2.08|
  |4|360|57.281|75795.220|2.12|
  |5|360|66.166|87488.569|2.45|
  |6|360|83.896|103499.177|2.90|
  |7|360|100.488|100812.133|2.83|
  |8|360|108.465|106740.810|2.99|

## Use Synthetic Data

To run this experiment, add these two parameters.

```bash
--use_synthetic_data="True" \
--src_max_len=100 \
```

- cudnn_lstm encoder and decoder

  |GPU number|batch size per GPU|total time to run 20 batches(s)|processing speed (words/second)|speed-up ratio|
  |:--|:--|:--|:--|:--|
  |1|360|28.176|51106.551||
  |2|360|31.722|90787.648|1.78|
  |3|360|37.075|116521.261|2.28|
  |4|360|42.303|136161.554|2.66|
  |5|360|47.482|151635.090|2.97|
  |6|360|53.096|162722.755|3.18|
  |7|360|60.311|167133.973|3.27|
  |8|360|69.595|165528.995|3.24|

- dynamic_rnn encoder and decoder

  |GPU number|batch size per GPU|total time to run 20 batches(s)|processing speed (words/second)|speed-up ratio|
  |:--|:--|:--|:--|:--|
  |1|360|36.497|39455.242||
  |2|360|41.340|69666.464|1.77|
  |3|360|47.367|91203.687|2.31|
  |4|360|54.651|105395.328|2.67|
  |5|360|61.107|117825.190|2.99|
  |6|360|68.696|125771.308|3.19|
  |7|360|75.263|133931.073|3.39|
  |8|360|83.640|137732.931|3.49|
